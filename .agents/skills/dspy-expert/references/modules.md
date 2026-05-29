# DSPy Modules

*Includes content from [dspy-agent-skills](https://github.com/intertwine/dspy-agent-skills) v0.2.3 ([`f2f7055`](https://github.com/intertwine/dspy-agent-skills/commit/f2f7055770e8c28f755a652e4d507da813a17c8a)).*

## `dspy.configure`

```python
dspy.configure(
    lm: dspy.BaseLM | None = None,
    track_usage: bool = False,
    async_max_workers: int = 8,
    adapter: dspy.Adapter | None = None,  # ChatAdapter / JSONAdapter / XMLAdapter
    callbacks: list[dspy.callbacks.BaseCallback] | None = None,
    warn_on_type_mismatch: bool = True,
)
```

Sets thread-local defaults. Use `dspy.context(...)` as a `with`-block to scope overrides.

DSPy 3.2.x warns by default when a module call passes extra input fields or values that don't match the signature's declared types. Treat those warnings as a callsite bug first; disable with `dspy.configure(warn_on_type_mismatch=False)` only if intentional.

## `dspy.LM`

```python
dspy.LM(
    model: str,                    # "provider/model-name"
    model_type: Literal["chat", "text", "responses"] = "chat",
    api_key: str | None = None,
    api_base: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    cache: bool = True,
    callbacks: list[BaseCallback] | None = None,
    num_retries: int = 3,
    provider: dspy.Provider | None = None,
    finetuning_model: str | None = None,
    launch_kwargs: dict | None = None,
    train_kwargs: dict | None = None,
    use_developer_role: bool = False,
    **kwargs,                      # forwarded to the provider backend
)
```

`.copy(rollout_id=n)` creates a deterministic variant that bypasses cache collisions.

## Built-in Modules

All modules inherit from `dspy.Module`. Use them directly or compose them.

| Module | Description | Typical Use |
|--------|-------------|-------------|
| `dspy.Predict` | Single LM call | Simple extraction, classification |
| `dspy.ChainOfThought` | CoT reasoning | Multi-step reasoning, explanation |
| `dspy.ProgramOfThought` | Code-based reasoning (needs Deno) | Math, symbolic computation |
| `dspy.ReAct` | Tool-use agent loop | Search, APIs, multi-tool agents |
| `dspy.CodeAct` | Python code execution (pure fns only) | Complex computations via code |
| `dspy.RLM` | Recursive LM — explores large contexts via REPL | Long documents, complex analysis (3.1.1+) |
| `dspy.MultiChainComparison` | Ensemble of CoT chains | High-accuracy QA |
| `dspy.Refine` | Iterative refinement with feedback | Quality improvement loops |
| `dspy.BestOfN` | Sample N independently, pick best | Reliability via sampling |
| `dspy.Parallel` | Run modules in parallel | Batch processing |

### Predictor constructors

| Class | Signature |
|---|---|
| `dspy.Predict` | `Predict(signature, callbacks=None, **config)` |
| `dspy.ChainOfThought` | `ChainOfThought(signature, rationale_field=None, rationale_field_type=str, **config)` |
| `dspy.ReAct` | `ReAct(signature: type[Signature], tools: list[Callable], max_iters: int = 20)` |
| `dspy.ProgramOfThought` | `ProgramOfThought(signature, max_iters: int = 3, interpreter=None)` |
| `dspy.RLM` | `RLM(signature, max_iterations=20, max_llm_calls=50, max_output_chars=10_000, verbose=False, tools=None, sub_lm=None, interpreter=None)` |

### Structured Outputs & Adapters
In modern DSPy (2.5+), structured outputs are achieved by using Pydantic types in your `Signature` and configuring an **Adapter**.

```python
import dspy
from pydantic import BaseModel, Field
from typing import List

class Person(BaseModel):
    name: str
    age: int = Field(ge=0, le=120)
    hobbies: List[str]

class Extraction(dspy.Signature):
    """Extract person details from text."""
    text: str = dspy.InputField()
    result: Person = dspy.OutputField()

dspy.configure(adapter=dspy.JSONAdapter())

extractor = dspy.Predict(Extraction)
response = extractor(text="Alice is 25 and likes climbing and painting.")
print(response.result.name, response.result.age)
```

Adapter options:
- `dspy.ChatAdapter` (default) — JSON-in-markdown with section headers.
- `dspy.JSONAdapter` — strict JSON I/O; best for tool-calling models.
- `dspy.XMLAdapter` — XML-tagged fields; good for Claude with complex structures.

**`dspy.BestOfN` vs `dspy.Refine`:**
- `BestOfN(module, N=5, reward_fn=fn, threshold=1.0)` — N **independent** runs, picks the best. No feedback between attempts.
- `Refine(module, N=3, reward_fn=fn, threshold=1.0)` — N runs **with automatic feedback**. After each failed attempt, DSPy generates hints ("Past Output" + "Instruction" fields) for the next run. Use `Refine` when each attempt can learn from the previous one.

**`dspy.CodeAct` constraint:** only pure Python functions as tools — no lambdas, callable objects, or external libraries:
```python
from dspy.predict import CodeAct   # note: not dspy.CodeAct directly
act = CodeAct("n -> factorial_result", tools=[factorial_fn], max_iters=3)
```

**`dspy.Parallel` full API (3.1.2: `timeout` and `straggler_limit` now exposed):**
```python
parallel = dspy.Parallel(num_threads=8, timeout=120, straggler_limit=0.9, return_failed_examples=False)
results = parallel([(module, example1), (module, example2)])

# Convenience: every dspy.Module has .batch()
results = my_module.batch(examples=[ex1, ex2, ex3], num_threads=4, return_failed_examples=True)
# If return_failed_examples=True: returns (results, failed_examples, exceptions)
```

**`dspy.RLM` — Recursive Language Model (3.1.1+):** See [rlm.md](rlm.md) for full deep dive.

**`dspy.LocalSandbox` for code execution:**
```python
sandbox = dspy.LocalSandbox()
result = sandbox.execute("value = 2*5 + 4\nvalue")  # returns 14
```

### Usage examples
```python
# Predict — basic
predictor = dspy.Predict("question -> answer")
result = predictor(question="What is 2+2?")
print(result.answer)

# ChainOfThought — adds step-by-step reasoning
cot = dspy.ChainOfThought("question -> answer")
result = cot(question="If a train travels 120km in 2h, what is its speed?")
print(result.reasoning, result.answer)

# ReAct — tool-using agent
def search_web(query: str) -> str:
    """Search the web for information."""
    ...  # your implementation

react = dspy.ReAct("question -> answer", tools=[search_web])
result = react(question="Who won the 2024 Olympics marathon?")

# ProgramOfThought — generates and executes Python code (requires Deno runtime)
pot = dspy.ProgramOfThought("question -> answer", max_iters=3)
result = pot(question="What is the sum of squares from 1 to 10?")
print(result.answer)  # "385"

# BestOfN — pick best of multiple samples
bon = dspy.BestOfN(dspy.ChainOfThought("question -> answer"), N=5, reward_fn=my_metric)

# Refine — iterative improvement
refine = dspy.Refine(dspy.ChainOfThought("draft -> refined"), N=3, reward_fn=quality_check)
```

---

## Custom Modules

Build complex programs by composing modules:

```python
class RAG(dspy.Module):
    def __init__(self, num_docs=5):
        self.num_docs = num_docs
        self.retrieve = dspy.Retrieve(k=num_docs)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        return self.generate(context=context, question=question)

class MultiHopRAG(dspy.Module):
    def __init__(self, hops=2):
        self.generate_query = [dspy.ChainOfThought("context, question -> query") for _ in range(hops)]
        self.generate_answer = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = []
        for i, gen_q in enumerate(self.generate_query):
            query = gen_q(context=context, question=question).query
            context += search(query)
        return self.generate_answer(context=context, question=question)
```

## `dspy.Module` API

- `module.forward(**kwargs)` — main logic
- `module(...)` — calls forward
- `module.named_predictors()` — iterate over all sub-predictors
- `module.set_lm(lm)` — set LM for all predictors in this module
- `module.get_lm()` — get the LM currently used by the module's predictors
- `module.batch(examples, num_threads=2, return_failed_examples=False)` — parallel execution
- `module.deepcopy()` — deep copy the module
- `module.reset_copy()` — copy with reset state
- `module.save(path)` / `module.load(path)` — persistence
- `module.dump_state()` / `.load_state(state)` — in-memory

## Custom LM backends (3.2.x)

If `dspy.LM("provider/model")` is not enough, subclass `dspy.BaseLM`:

```python
class MyLM(dspy.BaseLM):
    @property
    def supports_function_calling(self) -> bool:
        return False

    @property
    def supports_reasoning(self) -> bool:
        return False

    @property
    def supports_response_schema(self) -> bool:
        return False

    @property
    def supported_params(self) -> set[str]:
        return set()

    def forward(self, prompt=None, messages=None, **kwargs):
        ...
```

In 3.2.x, DSPy's adapters read capability properties directly from `BaseLM`, making custom backends less coupled to LiteLLM internals. If your provider throws a context-window exception, translate it to `dspy.ContextWindowExceededError(model=self.model, message=...)`.
