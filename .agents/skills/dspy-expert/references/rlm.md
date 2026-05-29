# `dspy.RLM` — Recursive Language Model

*Adapted from [dspy-agent-skills](https://github.com/intertwine/dspy-agent-skills) v0.2.3 ([`f2f7055`](https://github.com/intertwine/dspy-agent-skills/commit/f2f7055770e8c28f755a652e4d507da813a17c8a)).*

`dspy.RLM` runs the LLM in a sandboxed Python REPL (Pyodide/WASM via Deno) with access to the full context as variables. The LLM writes code to slice, grep, summarize, and recursively sub-query the data, iterating until it can answer. Use it when the context is too large to cram into a single prompt.

## Prerequisites

- **Deno installed** (for the default `PythonInterpreter`): `brew install deno` or see https://deno.land.
- A sub-LM for inner calls — usually a cheaper model than the outer LM.

## Canonical usage

```python
import dspy

dspy.configure(lm=dspy.LM("openai/gpt-4o"))
sub_lm = dspy.LM("openai/gpt-4o-mini")

rlm = dspy.RLM(
    "context, query -> answer",
    max_iterations=20,
    max_llm_calls=50,
    max_output_chars=10_000,
    sub_lm=sub_lm,
    tools=[],
    verbose=False,
)

result = rlm(
    context=open("huge_log.txt").read(),   # can be 500k+ tokens
    query="Summarize every unique error class and how many times each appeared.",
)
print(result.answer)
```

## Full constructor

```python
dspy.RLM(
    signature: type[Signature] | str,
    max_iterations: int = 20,       # REPL loop cap
    max_llm_calls: int = 50,        # sub-LM call cap (stops runaway recursion)
    max_output_chars: int = 10_000, # truncate REPL stdout per step
    verbose: bool = False,          # print the REPL trace
    tools: list[Callable] | None = None,
    sub_lm: dspy.LM | None = None,
    interpreter: CodeInterpreter | None = None,  # custom sandbox
)
```

## When to reach for RLM vs. alternatives

| Situation | Use |
|---|---|
| Context <100k, answer fits one LM call | `dspy.Predict` / `dspy.ChainOfThought` |
| Need external tools (web, db) | `dspy.ReAct(tools=[...])` |
| Math/code that must run | `dspy.ProgramOfThought` |
| **Huge context, recursive chunking, or data-exploration loop** | **`dspy.RLM`** |
| Entire-codebase reasoning where the LM should grep/read files | `dspy.RLM` with file-reading `tools=[...]` |

## Composition — RLM as a module inside a larger program

Wrap the RLM in your own `dspy.Module` and optimize the enclosing program with GEPA:

```python
class RepoAuditor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.explore = dspy.RLM("repo_tree, question -> findings",
                                max_iterations=30, sub_lm=dspy.LM("openai/gpt-4o-mini"))
        self.synth = dspy.ChainOfThought("findings, question -> report")

    def forward(self, repo_tree, question):
        f = self.explore(repo_tree=repo_tree, question=question).findings
        return self.synth(findings=f, question=question)
```

Then: `dspy.GEPA(metric=..., ...).compile(student=RepoAuditor(), trainset=..., valset=...)`.

## Tools

Tools are regular Python callables. DSPy introspects type hints and docstrings. In DSPy 3.2.x, tool dispatch is kwargs-only:

```python
def read_file(path: str) -> str:
    """Return the full text of a file."""
    return open(path).read()

rlm = dspy.RLM("repo, q -> answer", tools=[read_file])
```

Built-in REPL tools: `llm_query(prompt)`, `llm_query_batched(prompts)`, `SUBMIT(...)`.

## Practical tips

- **Budget carefully.** A single RLM call can issue dozens of sub-LM calls. Keep `max_llm_calls` tight (20–50).
- **Use a cheap `sub_lm`.** The outer LM orchestrates; inner calls don't need the flagship model.
- **Pass data as kwargs, not in the instruction.** `rlm(context=huge_string, query="...")` lets the REPL treat `context` as a Python variable.
- **`verbose=True` while debugging.** Prints every REPL step — invaluable when the RLM appears to hang.
- **Custom tools** via `tools=[...]`; exposed inside the sandbox. In DSPy 3.2.x they are invoked by keyword.
- **Deno install is required.** Missing Deno is the #1 RLM error.

## Security note

The default interpreter is a Deno-sandboxed Pyodide WASM runtime — no filesystem, network, or subprocess access by default. If you pass custom `tools` that do I/O, your tools' security posture is yours.

## Return value

Calling `rlm(...)` returns a `dspy.Prediction` with the signature's output fields. With `track_usage=True`, `.get_lm_usage()` aggregates tokens across every inner call.

## Common failures

| Symptom | Fix |
|---|---|
| `deno: command not found` | Install Deno. |
| `RLM hit max_iterations` | Raise `max_iterations`, or narrow the query. |
| `Sub-LM call count exceeded` | Raise `max_llm_calls`; check for infinite recursion in tools. |
| `Output truncated at 10000 chars` | Raise `max_output_chars`. |
| `KeyError` in final `.answer` | Print `verbose=True` trace to see why. |

## Anti-patterns

- Using RLM when a 32k-token prompt would fit — overhead is not worth it.
- Missing Deno → hard-to-diagnose failures.
- `max_llm_calls` left at default in a production path — runaway cost.
- Passing secrets in the `context` string — they get echoed into REPL state.
