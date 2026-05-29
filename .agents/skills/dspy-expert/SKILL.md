---
name: dspy-expert
description: "Expert guide for building AI programs with DSPy 3.2.x — the declarative framework for LM programming with automatic prompt optimization. Use this skill PROACTIVELY whenever: importing dspy, using Signatures/Modules/Optimizers, building RAG/agent/multi-hop pipelines, optimizing with GEPA/MIPROv2/BetterTogether, writing dspy.ChainOfThought/ReAct/Predict/CodeAct/RLM, evaluating with dspy.Evaluate, using dspy.Refine/BestOfN for output quality enforcement, configuring any LM provider, saving/loading compiled programs, integrating MCP tools, streaming, async, or debugging with inspect_history. Covers: LM config, Signatures, Modules, Optimizers, Evaluation, GEPA, RLM, Refine/BestOfN, Tools, Adapters, Streaming, Async, Multimodal, and Save/Load."
license: MIT
metadata:
  author: "leonvillamor + intertwine"
  version: "2.0.0"
  sources:
    - name: "skill-dspy (original)"
      url: "https://github.com/NeverSight/learn-skills.dev/tree/main/data/skills-md/leonvillamayor/skill-dspy/skill-dspy"
    - name: "dspy-agent-skills by intertwine"
      url: "https://github.com/intertwine/dspy-agent-skills"
      commit: "f2f7055770e8c28f755a652e4d507da813a17c8a"
      version: "v0.2.3"
  notes: "Merged skill combining original dspy-expert breadth with intertwine/dspy-agent-skills v0.2.3 depth on GEPA, evaluation, and advanced workflows. Validated against DSPy 3.2.x."
---

# DSPy Expert Guide (DSPy 3.2.x)

DSPy is the "PyTorch for prompts" — you declare **Signatures** (typed I/O contracts), compose them into **Modules**, and let optimizers (not you) tune the instructions and few-shot examples. Never write raw prompts.

## Core Mental Model

```
Signature  →  defines I/O schema (what to compute)
Module     →  implements a reasoning strategy (how to compute)
Optimizer  →  tunes prompts/weights automatically (how to improve)
Evaluate   →  measures quality (how to measure)
```

## Language Model Setup

DSPy uses [LiteLLM](https://litellm.ai/) under the hood, so any provider is supported.

```python
import dspy

# Configure globally
dspy.configure(lm=dspy.LM("openai/gpt-4o"), track_usage=True)

# Multiple LMs — use context managers for per-call override
with dspy.context(lm=dspy.LM("openai/gpt-4o")):
    result = my_module(question="...")

# For reasoning models (o3, o4), use model_type='responses'
dspy.LM("openai/o3-mini", model_type="responses")
```

Common provider prefixes: `openai/`, `anthropic/`, `azure/`, `vertex_ai/`, `bedrock/`, `ollama/`. For local Ollama: `dspy.LM("ollama_chat/llama3.1:8b", api_base="http://localhost:11434")`.

For a custom backend, subclass `dspy.BaseLM` — see [modules.md](references/modules.md).

## Signatures

Signatures define the _input/output schema_ of an LM call. Use the class form for production:

```python
from typing import Literal
from pydantic import BaseModel

class Classify(dspy.Signature):
    """Classify sentiment of a product review."""
    review: str = dspy.InputField()
    sentiment: Literal["positive", "negative", "neutral"] = dspy.OutputField()
    confidence: float = dspy.OutputField(desc="confidence score 0-1")
```

**Supported field types:** `str`, `int`, `float`, `bool`, `list[T]`, `dict[K,V]`, `Optional[T]`, `Literal[...]`, Pydantic `BaseModel`, `dspy.Image`, `dspy.Audio`, `dspy.History`, `dspy.Code`, `dspy.File`.

> **Deprecated:** `dspy.TypedPredictor(...)` — use `dspy.Predict` with Pydantic fields. `prefix=`, `format=`, `parser=` on fields are no-ops in 3.2.x.

## Predictor cheatsheet (DSPy 3.2.x)

| Predictor | When to use | Adds |
|---|---|---|
| `dspy.Predict(sig)` | Simple structured I/O | nothing |
| `dspy.ChainOfThought(sig)` | Reasoning tasks | a `reasoning` output field |
| `dspy.ReAct(sig, tools=[...], max_iters=20)` | Tool-using agent | Thought/Action/Observation loop |
| `dspy.ProgramOfThought(sig, max_iters=3)` | Math/data tasks | generates & runs Python (needs Deno) |
| `dspy.CodeAct(sig, tools=[...])` | Code execution (pure fns only) | Python code execution |
| `dspy.RLM(sig, ...)` | Long context / codebases | recursive REPL exploration |
| `dspy.Refine(module, N=3, reward_fn=fn)` | Quality improvement loops | iterative refinement with feedback |
| `dspy.BestOfN(module, N=5, reward_fn=fn)` | Reliability via sampling | N independent runs, pick best |

## Optimizer selection

| Optimizer | Best For | Data Needed | Notes |
|---|---|---|---|
| `dspy.GEPA` | **Default recommendation (2026)**. Reflective/evolutionary. | 50+ examples | Rich-feedback metric required. Beats MIPROv2 on complex tasks. |
| `dspy.MIPROv2` | Large trainsets, scalar metrics | 50-300 examples | Bayesian search over instructions + demos |
| `dspy.BetterTogether` | Multi-stage optimization | 100+ examples | Chains arbitrary named optimizers |
| `dspy.BootstrapFewShot` | Fast few-shot demos | 5-50 examples | Low signal |
| `dspy.COPRO` | Instruction-only | 20-100 examples | |
| `dspy.SIMBA` | Lighter reflective pass | 20-200 examples | Cheaper alternative to GEPA |
| `dspy.BootstrapFinetune` | Fine-tuning LM weights | 100+ examples | |

## Save & load

```python
# State-only (portable JSON; you must rebuild the architecture to load)
program.save("program.json", save_program=False)
new = QAProgram(); new.load("program.json")

# Full program (cloudpickle into a directory; restores everything)
program.save("./program_dir/", save_program=True)
restored = dspy.load("./program_dir/")
```

Prefer state-only for version control; full-program for deployment artifacts.

## Ten anti-patterns to refuse

1. Hard-coded prompt strings — write a Signature.
2. `dspy.TypedPredictor(...)` in new code — use `dspy.Predict` with Pydantic fields.
3. `dspy.OpenAI(...)` / `dspy.settings.configure(...)` — use `dspy.configure(lm=dspy.LM(...))`.
4. Provider-specific LM classes — use `dspy.LM("provider/model")` or subclass `dspy.BaseLM`.
5. Giant monolithic predictors — decompose into a `Module` with named sub-predictors.
6. Mutating `signature.instructions` by hand — let the optimizer do it.
7. In-lining few-shot demos in the Signature docstring — bootstrap/optimize them.
8. Using `pickle.dump(program)` — use `program.save(...)`.
9. Setting an LM per module without reason — configure globally, override only for model mixing.
10. Scalar-only metrics with GEPA — rich feedback is load-bearing. See [evaluation.md](references/evaluation.md).

## Deep Dives (Progressive Disclosure)

- **[modules.md](references/modules.md)**: All built-in modules (`Predict`, `ChainOfThought`, `ReAct`, `CodeAct`, `ProgramOfThought`, `RLM`, `MultiChainComparison`, `Parallel`), custom modules, `dspy.BaseLM`, adapters.
- **[evaluation.md](references/evaluation.md)**: Rich-feedback metrics for GEPA, `dspy.Evaluate` harness, dataset hygiene, CI-ready eval suites, LM-as-judge pattern.
- **[gepa.md](references/gepa.md)**: GEPA optimizer deep dive — canonical call, budget knobs, full constructor, BetterTogether chaining, data splits, resume/checkpoint.
- **[rlm.md](references/rlm.md)**: `dspy.RLM` for long-context reasoning — constructor, composition with GEPA, security, practical tips.
- **[workflow.md](references/workflow.md)**: 7-step end-to-end pipeline — spec → program → metric → baseline → GEPA → export.
- **[optimizers.md](references/optimizers.md)**: Full optimizer table with usage patterns for all optimizers (MIPROv2, COPRO, SIMBA, BootstrapFewShot, etc.).
- **[data_io.md](references/data_io.md)**: `dspy.Example`, `DataLoader`, multimodal types (`Image`, `Audio`, `History`), save/load details.
- **[advanced.md](references/advanced.md)**: Output quality enforcement (`Refine`, `BestOfN`), adapters (JSON/XML), tools & MCP, streaming & async, cache configuration.
- **[links.md](references/links.md)**: Official DSPy documentation and API reference links.

### Quick Patterns

```python
# Inspect LM calls
dspy.inspect_history(n=5)

# Debug type mismatches
dspy.configure(warn_on_type_mismatch=False)  # only if intentional
```

---

*Credits: This skill merges content from [skill-dspy by leonvillamayor](https://github.com/NeverSight/learn-skills.dev/tree/main/data/skills-md/leonvillamayor/skill-dspy/skill-dspy) and [dspy-agent-skills v0.2.3 by intertwine](https://github.com/intertwine/dspy-agent-skills) (commit [`f2f7055`](https://github.com/intertwine/dspy-agent-skills/commit/f2f7055770e8c28f755a652e4d507da813a17c8a)), validated against DSPy 3.2.x.*
