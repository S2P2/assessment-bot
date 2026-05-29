# DSPy Advanced Workflow (2026)

*Adapted from [dspy-agent-skills](https://github.com/intertwine/dspy-agent-skills) v0.2.3 ([`f2f7055`](https://github.com/intertwine/dspy-agent-skills/commit/f2f7055770e8c28f755a652e4d507da813a17c8a)).*

This skill runs the seven-step loop that turns a natural-language task description into an optimized, saved, deployable DSPy program. Every step delegates to a specific reference file — invoke them in order.

## The seven steps

### 1. Spec

Rephrase the user's task in one sentence. Identify inputs, outputs, the quality axis that matters, and any constraints (latency, cost, tool access, context size). Pick predictor shape:

| Task shape | Predictor |
|---|---|
| Single-step structured I/O | `dspy.Predict` / `dspy.ChainOfThought` |
| Tool use / multi-step | `dspy.ReAct` |
| Code execution | `dspy.ProgramOfThought` |
| Long context / codebase | `dspy.RLM` → [rlm.md](rlm.md) |

### 2. Program

Write the typed `dspy.Signature` + `dspy.Module` subclass per [modules.md](modules.md). No hard-coded prompts. Keep predictors named so GEPA can target them.

### 3. Data

Build `trainset` and **separate** `valset` as `dspy.Example(...).with_inputs(...)`. For GEPA, maximize trainset size and keep validation just large enough to represent downstream behavior; held-out `testset` is reported on at the end only. See [evaluation.md](evaluation.md) and [data_io.md](data_io.md).

### 4. Rich metric

Write `rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None)` returning `dspy.Prediction(score=0..1, feedback="natural-language critique")`. The feedback is load-bearing — it's what GEPA's reflection LM learns from. A dict with the same fields crashes `dspy.Evaluate`; only `dspy.Prediction` aggregates correctly. See [evaluation.md](evaluation.md).

### 5. Baseline

```python
evaluator = dspy.Evaluate(devset=valset, metric=rich_metric,
                          num_threads=8, display_progress=True,
                          provide_traceback=True,
                          save_as_json="runs/baseline.json")
baseline = evaluator(program)
print("Baseline:", baseline.score)
```

### 6. GEPA optimize

```python
reflection_lm = dspy.LM("openai/gpt-5", temperature=1.0, max_tokens=32000)
optimizer = dspy.GEPA(
    metric=rich_metric,
    auto="medium",
    reflection_lm=reflection_lm,
    candidate_selection_strategy="pareto",
    track_stats=True,
    track_best_outputs=True,
    log_dir="./gepa_logs",
    num_threads=8,
    seed=0,
)
optimized = optimizer.compile(student=program, trainset=trainset, valset=valset)
print("Optimized:", evaluator(optimized).score)
```

Run `auto="light"` first as a sanity check; move to `auto="medium"`/`"heavy"` for the final run. See [gepa.md](gepa.md).

For multi-stage compile, DSPy 3.2.x also exposes `dspy.BetterTogether(metric=..., bootstrap=..., gepa=...)`.

### 7. Export & deploy

```python
optimized.save("artifacts/program.json", save_program=False)     # state, portable
# or for full deployment artifact:
optimized.save("artifacts/program_dir/", save_program=True)
```

Deploy:
- Load with `dspy.load("artifacts/program_dir/")` or reconstruct + `.load("program.json")`.
- Wrap in FastAPI/CLI.
- Enable `track_usage=True` for cost/latency observability.
- Log with MLflow (`mlflow.dspy.autolog()`) or W&B in CI.
- Keep an offline regression test that runs the `evaluator` against the saved program and fails CI below a threshold.

## Full orchestration template

```python
"""DSPy end-to-end pipeline — spec → optimize → deploy."""

import dspy
from pathlib import Path

# ----- 1–2. Spec & program (modules.md) -----
class MyTask(dspy.Signature):
    """<one-line instruction from the spec>."""
    input_field: str = dspy.InputField()
    output_field: str = dspy.OutputField()

class MyProgram(dspy.Module):
    def __init__(self):
        super().__init__()
        self.step = dspy.ChainOfThought(MyTask)
    def forward(self, **kw):
        return self.step(**kw)

# ----- 3. Data (evaluation.md, data_io.md) -----
trainset = [...]   # list[dspy.Example(...).with_inputs(...)]
valset   = [...]

# ----- 4. Rich metric (evaluation.md) -----
def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    score = ...          # compute 0..1
    feedback = ...       # detailed critique
    return dspy.Prediction(score=score, feedback=feedback)  # NOT a dict

# ----- 5. Baseline -----
dspy.configure(lm=dspy.LM("openai/gpt-4o"), track_usage=True)
evaluator = dspy.Evaluate(devset=valset, metric=rich_metric, num_threads=8,
                          display_progress=True, provide_traceback=True,
                          save_as_json="runs/baseline.json")
program = MyProgram()
print("Baseline:", evaluator(program).score)

# ----- 6. GEPA optimize (gepa.md) -----
optimizer = dspy.GEPA(
    metric=rich_metric,
    auto="medium",
    reflection_lm=dspy.LM("openai/gpt-5", temperature=1.0, max_tokens=32000),
    candidate_selection_strategy="pareto",
    track_stats=True, track_best_outputs=True,
    log_dir="./gepa_logs", num_threads=8, seed=0,
)
optimized = optimizer.compile(student=program, trainset=trainset, valset=valset)
print("Optimized:", evaluator(optimized).score)

# ----- 7. Export (data_io.md) -----
Path("artifacts").mkdir(exist_ok=True)
optimized.save("artifacts/program.json", save_program=False)
```

## Guardrails

- Never skip step 4 (rich metric). GEPA without feedback ≈ random search.
- Always baseline before optimizing — no baseline, no claim.
- Save both pre- and post-optimization metrics to JSON for auditability.
- If held-out test score drops post-optimization, your valset is too narrow. Expand valset and re-run.
- Freeze optimized program with `module._compiled = True` before multi-stage re-compilation.

## Step-by-step failure modes

| Step | Common failure | Fix |
|---|---|---|
| 1. Spec | Signature too broad ("do the task") | One-sentence instruction; name specific inputs/outputs |
| 2. Program | Hard-coded prompts in `forward()` | Let predictors own instructions; GEPA can't mutate strings |
| 3. Data | `trainset == valset` | Always split; overlap causes GEPA to overfit silently |
| 3. Data | Tiny trainset | GEPA's reflection loop needs enough varied failures |
| 4. Metric | Generic feedback ("wrong") | Cite the specific field, expected vs. actual, and why |
| 4. Metric | Returns a dict instead of `dspy.Prediction` | `dspy.Evaluate` crashes: `TypeError: int + dict` |
| 5. Baseline | Skipped entirely | No baseline means no claim of improvement |
| 6. GEPA | `reflection_lm` is None | GEPA asserts at construction time, not compile time |
| 6. GEPA | Plateau after round 1–2 | Weak feedback, small `reflection_minibatch_size`, or model saturation |
| 7. Export | `save_program=True` on untested code | Prefer `save_program=False` (state-only) unless deploying standalone |
