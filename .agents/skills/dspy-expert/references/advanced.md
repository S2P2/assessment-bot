# DSPy Advanced Features

## Cache Configuration

DSPy caches LM responses locally by default to save costs and speed up iterations.

```python
# Configure cache (enabled by default)
dspy.configure(cache=True)

# To disable cache for a specific call
with dspy.context(cache=False):
    result = my_module(question="...")

# Set a custom cache path (default is ~/.dspy/cache)
import os
os.environ["DSPY_CACHEBOOL"] = "True"
os.environ["DSPY_CACHEDIR"] = "./my_cache"
```

## Output Quality Enforcement (Refine / BestOfN)
...

**`dspy.Assert` and `dspy.Suggest` were deprecated and removed in DSPy 3.1.x.** Use `dspy.Refine` or `dspy.BestOfN` instead.

### `dspy.Refine` — iterative refinement with automatic feedback

After each failed attempt, DSPy automatically generates feedback ("Past Output" + "Instruction" fields) and feeds it to the next attempt. Use when each retry can learn from the previous one.

```python
def quality_check(example, pred, trace=None):
    """Return a float 0-1 or bool. Refine retries until threshold is met."""
    return len(pred.answer) > 10 and pred.answer[0].isupper()

class QAModule(dspy.Module):
    def __init__(self):
        self.generate = dspy.ChainOfThought("question -> answer")
    def forward(self, question):
        return self.generate(question=question)

# Wrap any module with Refine
refined = dspy.Refine(
    module=QAModule(),
    N=3,              # max attempts (default 3)
    reward_fn=quality_check,
    threshold=1.0,    # reward must reach this to stop early
)
result = refined(question="What is DSPy?")
```

### `dspy.BestOfN` — N independent samples, pick best

Runs N **independent** calls (no feedback between them) and returns the one with the highest reward. Simpler but uses more tokens.

```python
def my_metric(example, pred, trace=None):
    return float(pred.answer.lower().count("dspy") > 0)

best = dspy.BestOfN(
    module=dspy.ChainOfThought("question -> answer"),
    N=5,              # number of independent samples
    reward_fn=my_metric,
    threshold=1.0,    # stop early if reward reaches this
)
result = best(question="Explain DSPy in one sentence.")
```
---

## Adapters (JSON / XML)

Adapters translate your high-level `Signature` into specific prompt formats (e.g., JSON schemas or XML tags) for different LMs.

### JSONAdapter
Best for OpenAI, Gemini, and Llama-3. Forces the model to return a valid JSON object matching your signature.

```python
# Configure globally
dspy.configure(adapter=dspy.JSONAdapter())

# Or use per-call via context manager
with dspy.context(adapter=dspy.JSONAdapter()):
    result = extractor(text="Apple released the iPhone in Cupertino.")
    print(result.entities) # ['Apple', 'iPhone', 'Cupertino']
```

### XMLAdapter
Best for Anthropic (Claude) or models that perform better with XML-tagged structures.

```python
with dspy.context(adapter=dspy.XMLAdapter()):
    summarize = dspy.Predict("document -> summary")
    response = summarize(document="DSPy is a framework for programming LMs...")
```

---

## Tools & MCP

DSPy integrates tools via the `dspy.Tool` wrapper, which provides the necessary metadata for agents like `ReAct` or `CodeAct`.

```python
import datetime

# Define a standard Python function
def get_current_time(location: str) -> str:
    """Returns the current time for a given location."""
    return f"The time in {location} is {datetime.datetime.now().strftime('%H:%M:%S')}"

# Wrap as a DSPy Tool
time_tool = dspy.Tool(get_current_time)

# Integrate into a ReAct agent
agent = dspy.ReAct("question -> answer", tools=[time_tool])

# MCP tool integration (async)
...

from mcp import ClientSession
dspy_tool = dspy.Tool.from_mcp_tool(session, mcp_tool_object)
agent = dspy.ReAct("question -> answer", tools=[dspy_tool])
```

---

## Streaming & Async

```python
# Async modules
class AsyncModule(dspy.Module):
    async def aforward(self, question):
        return await self.generate(question=question)

# Streaming
for event in dspy.streamify(my_module(question="...")):
    print(event)
```
