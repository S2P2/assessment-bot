---
name: dspy-expert
description: "Expert guide for building AI programs with DSPy — the declarative framework for LM programming with automatic prompt optimization. Use this skill PROACTIVELY whenever: importing dspy, using Signatures/Modules/Optimizers, building RAG/agent/multi-hop pipelines, optimizing with BootstrapFewShot/MIPROv2/COPRO/SIMBA/GEPA/BetterTogether, writing dspy.ChainOfThought/ReAct/Predict/CodeAct, evaluating with dspy.Evaluate, using dspy.Refine/BestOfN for output quality enforcement, configuring any LM provider (OpenAI/Anthropic/Gemini/Ollama/reasoning models), saving/loading compiled programs, integrating MCP tools (stdio or HTTP), streaming, async modules, tracking token usage, or debugging with inspect_history. Covers: LM config, Signatures, Modules, Optimizers, Evaluation, Refine/BestOfN, Tools, Adapters, Streaming, Async, Callbacks, Embeddings, and Save/Load."
license: MIT
metadata:
  author: skill-dspy
  version: "1.0.0"
  source: "https://github.com/NeverSight/learn-skills.dev/tree/main/data/skills-md/leonvillamayor/skill-dspy/skill-dspy"
  notes: "Added MIPROv2, JSONAdapter, Pydantic signatures, and Cache examples (v3.3.0). Removed all section numbering for modularity."
---

# DSPy Expert Guide

DSPy is a declarative framework for programming language models. Instead of hand-writing prompts, you define _what_ your program should do (via Signatures and Modules), and DSPy figures out _how_ to prompt the LM to do it — including automatic optimization.

## Core Mental Model

```
Signature  →  defines I/O schema (what to compute)
Module     →  implements a reasoning strategy (how to compute)
Optimizer  →  tunes prompts/weights automatically (how to improve)
Evaluate   →  measures quality (how to measure)
```

---

## Language Model Setup

DSPy uses [LiteLLM](https://litellm.ai/) under the hood, so any provider is supported.

```python
import dspy

# OpenAI
lm = dspy.LM('openai/gpt-4o-mini', api_key='YOUR_KEY')

# Configure globally
dspy.configure(lm=lm)

# Multiple LMs — use context managers for per-call override
with dspy.context(lm=dspy.LM('openai/gpt-4o')):
    result = my_module(question="...")
```

**Key configuration:** `dspy.configure(lm=lm, track_usage=True)` enables token usage tracking. For reasoning models (o3, o4), use `model_type='responses'`.

---

## Signatures

Signatures define the _input/output schema_ of an LM call.

```python
class Classify(dspy.Signature):
    """Classify sentiment of a product review."""
    review: str = dspy.InputField()
    sentiment: Literal["positive", "negative", "neutral"] = dspy.OutputField()
    confidence: float = dspy.OutputField(desc="confidence score 0-1")
```

**Supported field types:** `str`, `int`, `float`, `bool`, `list[T]`, `dict[K,V]`, `Optional[T]`, `TypedDict`, `Literal[...]`, `dspy.Image`, `dspy.Audio`, `dspy.History`, `dspy.Code`, `dspy.File`, and **Pydantic models** (`BaseModel`).

**TypedPredictor:** When using complex Pydantic types, use `dspy.TypedPredictor(Signature)` for automatic validation and parsing.

---

## Deep Dives (Progressive Disclosure)

- **[Modules.md](references/modules.md)**: Built-in modules (`Predict`, `ChainOfThought`, `ReAct`, `CodeAct`, `ProgramOfThought`, `RLM`) and how to build custom modules.
- **[Data_IO.md](references/data_io.md)**: Managing examples (`dspy.Example`), loading data (`DataLoader`), multimodal types (`Image`, `Audio`), conversation history (`dspy.History`), and saving/loading compiled programs.
- **[Advanced.md](references/advanced.md)**: Output quality enforcement (`Refine`, `BestOfN`), tools (Python functions, MCP), streaming, and async.
- **[Optimizers.md](references/optimizers.md)**: Automatic prompt optimization (`MIPROv2`, `BootstrapFewShot`, `COPRO`, `SIMBA`, `GEPA`) and `dspy.Evaluate`.
- **[Links.md](references/links.md)**: Official DSPy overview and documentation links.

### Quick Patterns

#### Inspect LM calls

```python
dspy.inspect_history(n=5)   # show last 5 LM interactions
```
