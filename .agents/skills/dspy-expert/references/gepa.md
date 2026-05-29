# DSPy GEPA Optimizer (3.2.x)

*Adapted from [dspy-agent-skills](https://github.com/intertwine/dspy-agent-skills) v0.2.3 ([`f2f7055`](https://github.com/intertwine/dspy-agent-skills/commit/f2f7055770e8c28f755a652e4d507da813a17c8a)).*

GEPA (Genetic-Pareto) is a reflective optimizer: it mutates a program's instructions and few-shots using an LM that reads your metric's **textual feedback** and proposes improvements. It maintains a Pareto frontier across validation tasks and is the default recommendation for complex DSPy workloads in 2026.

> The expansion "Genetic-Evolutionary Prompt Adaptation" that appears in some AI-generated summaries is an LLM-hallucinated backronym. The [paper](https://arxiv.org/abs/2507.19457) defines GEPA as Genetic-Pareto; the "Pareto" is load-bearing (GEPA keeps a frontier of candidates rather than collapsing to one).

## Prerequisites — do these first or GEPA wastes rollouts

1. A `dspy.Module` that runs end-to-end (see [modules.md](modules.md)).
2. A rich-feedback metric returning `dspy.Prediction(score=float, feedback=str)` (see [evaluation.md](evaluation.md)). **A float-only metric makes GEPA no better than MIPRO.**
3. `trainset` and a **separate** `valset`. For GEPA, maximize training examples and keep validation just large enough to represent the downstream distribution.
4. A `reflection_lm` — a strong LM (often the same or stronger than the task LM) set to `temperature=1.0` for creative proposals.

## Canonical call

```python
import dspy

dspy.configure(lm=dspy.LM("openai/gpt-5-mini"))
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

optimized.save("optimized_program.json", save_program=False)
```

## Import paths

```python
import dspy
dspy.GEPA(...)                              # preferred
# equivalently:
from dspy.teleprompt import GEPA
```

## Metric contract (precise)

```python
def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    score = ...      # 0.0..1.0
    feedback = ...   # detailed natural-language critique
    return dspy.Prediction(score=score, feedback=feedback)  # NOT a dict
```

**Return `dspy.Prediction`, not a dict.** `dspy.Evaluate` in DSPy 3.2.1 crashes on a literal dict metric (`TypeError: unsupported operand type(s) for +: 'int' and 'dict'`).

- `pred_name` / `pred_trace` are set during reflection on a specific predictor — write per-predictor feedback when possible (credit assignment).

## Budget knobs

Use **either** `auto=...` **or** explicit budget — not both.

| Mode | Rough rollouts | When to use |
|---|---|---|
| `auto="light"` | ~20–40 full evals | Sanity-check GEPA works on your metric |
| `auto="medium"` | ~80–150 full evals | Everyday optimization |
| `auto="heavy"` | ~300–600 full evals | Final run before ship |
| `max_full_evals=N` | Explicit | Deterministic budget |
| `max_metric_calls=N` | Explicit | Hard cap on metric invocations (more predictable cost) |

Each "full eval" ≈ `len(valset)` metric calls. Budget accordingly for cost.

## Full constructor (DSPy 3.2.x)

```python
dspy.GEPA(
    metric,                                  # required
    auto=None,                               # Literal["light","medium","heavy"] | None
    max_full_evals=None,
    max_metric_calls=None,
    reflection_minibatch_size=3,
    candidate_selection_strategy="pareto",   # or "current_best"
    reflection_lm=None,                      # required in practice
    skip_perfect_score=True,
    add_format_failure_as_feedback=False,
    instruction_proposer=None,               # custom ProposalFn
    component_selector="round_robin",        # or "all" or a callable
    use_merge=True,
    max_merge_invocations=5,
    num_threads=None,
    failure_score=0.0,
    perfect_score=1.0,
    log_dir=None,
    track_stats=False,
    use_wandb=False,
    wandb_api_key=None,
    wandb_init_kwargs=None,
    track_best_outputs=False,
    warn_on_score_mismatch=True,
    use_mlflow=False,
    seed=0,
    gepa_kwargs=None,                        # e.g. {"use_cloudpickle": True}
)
```

`.compile(student, *, trainset, valset=None, teacher=None)` — `teacher` is not currently used.

## Data split guidance

GEPA is different from other optimizers: **maximize the training set** and reserve only enough validation examples to represent downstream behavior. GEPA learns from traces and textual feedback on training examples, so starving trainset hurts.

## BetterTogether in DSPy 3.2.x

Chains arbitrary named optimizers:

```python
optimizer = dspy.BetterTogether(
    metric=rich_metric,
    bootstrap=dspy.BootstrapFewShotWithRandomSearch(metric=rich_metric),
    gepa=dspy.GEPA(metric=rich_metric, auto="light", reflection_lm=reflection_lm),
)

optimized = optimizer.compile(
    student=program,
    trainset=trainset,
    valset=valset,
    strategy="bootstrap -> gepa",
)
```

Pass `strategy=` explicitly when you use named stages. DSPy 3.2.1's default remains `"p -> w -> p"`, which assumes keys are literally `p` and `w`.

## When GEPA > MIPROv2

- Your metric can produce specific, teachable critiques.
- The program has multiple predictors that need targeted improvements.
- Rollout budget is small (GEPA converges faster with rich feedback).

## When MIPROv2 > GEPA

- Metric is scalar-only — use `dspy.MIPROv2`.
- You want pure few-shot bootstrapping with no instruction mutation.
- Very large trainset (500+) where Bayesian search over demos pays off.

## When SIMBA is worth trying

`dspy.SIMBA` is a lighter reflective optimizer. Try it for quick exploration before a full GEPA run.

## Resume & checkpointing

`log_dir` writes candidate programs + scores per round. To resume an interrupted run, point `log_dir` at the same directory.

## Inference-time best-of with `track_best_outputs`

With `track_best_outputs=True`, GEPA records, per task, the best prediction seen across all candidates. Access via `optimized.detailed_results.best_outputs_valset`.

## Anti-patterns

- Float-only metric with no feedback — GEPA collapses to random search.
- Same set used for train and val — Pareto selection overfits.
- `reflection_lm` = small model — it can't critique; use the strongest LM you can afford.
- Running `auto="heavy"` on an untested metric — burn money. Run `auto="light"` first.
- Ignoring `log_dir` — losing a 4-hour run to a disconnect is very painful.

## Gotcha: `reflection_lm` is required at construction, not compile

`dspy.GEPA(...)` asserts `reflection_lm is not None` at init time — you cannot defer it to `.compile()`.

## Tuning guide

| Symptom | Lever |
|---|---|
| No improvement in first rounds | Check metric feedback is specific, not generic. Raise `reflection_lm` strength. |
| Oscillates between candidates | Lower `reflection_minibatch_size` from 3 to 2; prefer `candidate_selection_strategy="pareto"`. |
| OOM during reflection | Lower `reflection_lm` `max_tokens`; reduce trainset size. |
| Cost too high | Set explicit `max_metric_calls` instead of `auto="heavy"`. |
| Optimized program worse on held-out test | Valset too small / not representative; expand valset, set `skip_perfect_score=True`. |
