# DSPy Modules

## Built-in Modules

All modules inherit from `dspy.Module`. Use them directly or compose them.

| Module | Description | Typical Use |
|--------|-------------|-------------|
| `dspy.Predict` | Single LM call | Simple extraction, classification |
| `dspy.TypedPredictor` | Structured LM call | Validation of Pydantic models / complex types |
| `dspy.ChainOfThought` | CoT reasoning | Multi-step reasoning, explanation |
| `dspy.ProgramOfThought` | Code-based reasoning (needs Deno) | Math, symbolic computation |
| `dspy.ReAct` | Tool-use agent loop | Search, APIs, multi-tool agents |
| `dspy.CodeAct` | Python code execution (pure fns only) | Complex computations via code |
| `dspy.RLM` | Recursive LM — explores large contexts via REPL | Long documents, complex analysis (3.1.1+) |
| `dspy.MultiChainComparison` | Ensemble of CoT chains | High-accuracy QA |
| `dspy.Refine` | Iterative refinement with feedback | Quality improvement loops |
| `dspy.BestOfN` | Sample N independently, pick best | Reliability via sampling |
| `dspy.Parallel` | Run modules in parallel | Batch processing |

### TypedPredictor & Pydantic Signatures
Use `dspy.TypedPredictor` to enforce Pydantic validation on signature outputs.

```python
from pydantic import BaseModel, Field
from typing import List, Literal

class Person(BaseModel):
    name: str
    age: int = Field(ge=0, le=120)
    hobbies: List[str]

class Extraction(dspy.Signature):
    """Extract person details from text."""
    text: str = dspy.InputField()
    result: Person = dspy.OutputField()

# TypedPredictor handles the structured parsing
extractor = dspy.TypedPredictor(Extraction)
response = extractor(text="Alice is 25 and likes climbing and painting.")
print(response.result.name, response.result.age)
```

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

**`dspy.RLM` — Recursive Language Model (3.1.1+):** Explores large contexts via sandboxed Python REPL. Requires Deno.
```python
rlm = dspy.RLM(
    signature="context, query -> answer",
    max_iterations=20,      # maximum REPL loops
    max_llm_calls=50,       # maximum sub-LM calls
    sub_lm=None,            # optional cheaper model for sub-queries
    tools=None,             # list of custom tool functions
)
result = rlm(context="...very large document...", query="What is the revenue?")
print(result.answer)
print(result.trajectory)       # list of {code, output} steps
```
Built-in REPL tools: `llm_query(prompt)`, `llm_query_batched(prompts)`, `SUBMIT(...)`. Also supports `aforward()` for async.

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
# ProgramOfThought writes Python code, executes it in a sandbox, and extracts the answer.
# Ideal for math, symbolic computation, and data manipulation tasks.

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
        self.retrieve = dspy.Retrieve(k=num_docs)          # if using a retriever
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
            context += search(query)   # your search function
        return self.generate_answer(context=context, question=question)
```

**Module API:**
- `module.forward(**kwargs)` — main logic
- `module(...)` — calls forward
- `module.named_predictors()` — iterate over all sub-predictors
- `module.set_lm(lm)` — set LM for all predictors in this module
- `module.get_lm()` — get the LM currently used by the module's predictors
- `module.batch(examples, num_threads=2, return_failed_examples=False)` — run module on a list of examples in parallel (returns list of results; if `return_failed_examples=True`, returns `(results, failed_examples, exceptions)`)
- `module.deepcopy()` — deep copy the module
- `module.reset_copy()` — copy with reset state
- `module.save(path)` / `module.load(path)` — persistence
