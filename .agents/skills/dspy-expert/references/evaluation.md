# DSPy Evaluation Harness (3.2.x)

*Adapted from [dspy-agent-skills](https://github.com/intertwine/dspy-agent-skills) v0.2.3 ([`f2f7055`](https://github.com/intertwine/dspy-agent-skills/commit/f2f7055770e8c28f755a652e4d507da813a17c8a)).*

The metric is usually more important than the program. For `dspy.GEPA` especially, the quality of **textual feedback** in your metric determines whether optimization converges.

## Two rules

1. **Return a `dspy.Prediction(score=..., feedback=...)`, not a dict.** `dspy.Evaluate`'s parallel executor aggregates scores via sum, which breaks on dict outputs (`TypeError: unsupported operand type(s) for +: 'int' and 'dict'`). `dspy.Prediction` supports `__float__`/`__add__` and is what GEPA's adapter natively unwraps. A bare float still works for pure `dspy.Evaluate` scoring, but GEPA needs the score+feedback pair.
2. **Separate valset.** Never optimize and evaluate on the same examples. Optimizers overfit fast.

## Canonical rich-feedback metric

```python
import dspy

def rich_metric(gold: dspy.Example, pred: dspy.Prediction, trace=None,
                pred_name: str | None = None, pred_trace=None):
    # 1. Compute sub-scores — multi-axis beats scalar
    correctness = 1.0 if _normalize(pred.answer) == _normalize(gold.answer) else 0.0
    cited = _has_citation(pred.answer, gold.sources) if hasattr(gold, "sources") else 1.0
    concise = 1.0 if len(pred.answer.split()) <= 50 else 0.5
    score = 0.6 * correctness + 0.25 * cited + 0.15 * concise

    # 2. Write feedback that teaches the optimizer
    parts = []
    if correctness < 1.0:
        parts.append(
            f"Answer mismatch. Predicted: {pred.answer!r}. Expected: {gold.answer!r}. "
            f"Likely cause: reasoning skipped the units/quantity in the question."
        )
    if cited < 1.0:
        parts.append("Did not ground the claim in the provided sources. Quote a source fragment.")
    if concise < 1.0:
        parts.append("Answer exceeded 50 words — tighten to one sentence.")
    if not parts:
        parts.append("Correct, grounded, and concise.")
    feedback = " ".join(parts)

    return dspy.Prediction(score=score, feedback=feedback)
```

## Metric signatures

A metric callable receives:

```python
metric(
    gold: dspy.Example,          # ground-truth example
    pred: dspy.Prediction,       # program output
    trace: DSPyTrace | None = None,     # set during .compile()
    pred_name: str | None = None,       # GEPA only — which predictor
    pred_trace: DSPyTrace | None = None, # GEPA only — that predictor's trace
) -> float | dspy.Prediction | bool
```

Return values:
- `float` — treated as the score; works with `dspy.Evaluate` and most optimizers.
- **`dspy.Prediction(score=float, feedback=str)`** — GEPA-compatible; feedback is fed to the reflection LM. **Recommended for any metric used with an optimizer.**
- `bool` — treated as 0.0 / 1.0.

**Why not a dict?** `dspy.Evaluate` aggregates via `sum()`. A literal dict crashes with `TypeError: unsupported operand type(s) for +: 'int' and 'dict'` under DSPy 3.2.1.

GEPA's per-predictor feedback: when `pred_name` is non-None, return feedback targeted at *that* predictor's trace. This lets GEPA assign credit.

## Canonical harness

```python
evaluator = dspy.Evaluate(
    devset=valset,
    metric=rich_metric,
    num_threads=8,
    display_progress=True,
    display_table=10,
    provide_traceback=True,
    max_errors=5,
    failure_score=0.0,
    save_as_json="eval_runs/baseline.json",
)
result = evaluator(program)
print("Overall:", result.score)
for example_result in result.results[:3]:
    print(example_result)
```

`dspy.Evaluate` returns an `EvaluationResult` with `.score` (aggregate float) and `.results` (list of `(example, pred, score)` tuples).

## `dspy.Evaluate` API

```python
dspy.Evaluate(
    devset: list[dspy.Example],
    metric: Callable | None = None,
    num_threads: int | None = None,
    display_progress: bool = False,
    display_table: bool | int = False,   # True = all rows; int = first N
    max_errors: int | None = None,
    provide_traceback: bool | None = None,
    failure_score: float = 0.0,
    save_as_csv: str | None = None,
    save_as_json: str | None = None,
)
```

## LM-as-judge metric pattern

```python
class Judge(dspy.Signature):
    """Score the predicted answer 0.0–1.0 for factual correctness and cite the weakness."""
    question: str = dspy.InputField()
    gold_answer: str = dspy.InputField()
    pred_answer: str = dspy.InputField()
    score: float = dspy.OutputField()
    critique: str = dspy.OutputField()

judge = dspy.ChainOfThought(Judge)

def judge_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    j = judge(question=gold.question, gold_answer=gold.answer, pred_answer=pred.answer)
    return dspy.Prediction(score=float(j.score), feedback=j.critique)
```

Use a stronger LM for the judge than for the program under test (`dspy.context(lm=strong_lm): judge(...)`).

## Built-in metrics

```python
dspy.evaluate.answer_exact_match      # exact string match
dspy.evaluate.answer_passage_match    # answer appears in passage
dspy.SemanticF1()                     # LM-based semantic F1 score
dspy.CompleteAndGrounded()            # checks completeness and grounding in context
```

## Dataset hygiene

- **Size**: 20–50 examples is enough for GEPA's reflective loop; 100–500 for MIPROv2-style bootstrapping.
- **Split**: hand-curate two disjoint sets — `trainset` (for optimization) and `valset` (for metric-on-optimized-program). A test set you *never* look at during development is gold.
- **Representativeness** beats size. Include edge cases, ambiguity, adversarial inputs.
- Build `dspy.Example(...).with_inputs("question", "context")` — the `with_inputs` call marks which fields are inputs vs. gold outputs.

```python
trainset = [
    dspy.Example(question="…", answer="…").with_inputs("question"),
    ...
]
```

## Multi-axis metrics (recommended)

Combine correctness, faithfulness, format adherence, latency, and cost. Each axis should be a 0–1 float with a written definition. Weight them explicitly; don't hide weights inside magic numbers — make them constants.

## CI-ready eval suite

```python
# tests/test_dspy_eval.py
import dspy, pytest
from my_program import program, valset, rich_metric

@pytest.fixture(scope="module")
def evaluator():
    return dspy.Evaluate(devset=valset, metric=rich_metric, num_threads=8,
                         display_progress=False, provide_traceback=True)

def test_program_meets_threshold(evaluator):
    result = evaluator(program)
    assert result.score >= 0.75, f"Regression: {result.score:.3f}"
```

## Tracing & observability

- `track_usage=True` on `dspy.configure` accumulates token counts on predictions (`pred.get_lm_usage()`).
- MLflow: `import mlflow; mlflow.dspy.autolog()` → traces every prediction.
- W&B: pass `use_wandb=True` to `dspy.GEPA`.
- OpenTelemetry: `dspy.settings.configure(callbacks=[OTelCallback()])`.

## Anti-patterns

- Scalar-only metrics (float but no feedback) when using GEPA — wasted signal.
- **`return {"score": s, "feedback": f}` (dict)** — crashes `dspy.Evaluate`'s parallel aggregator. Use `dspy.Prediction(score=s, feedback=f)`.
- Exact-match metrics on open-ended generation tasks — use semantic or LM-as-judge scoring.
- Evaluating on the trainset — optimistic by 10–30 points.
- Silently swallowing exceptions (`provide_traceback=False`) — you'll blame the LM for a KeyError.
- Changing the metric mid-experiment without re-baselining — prior numbers become incomparable.

## Common failure modes

| Symptom | Likely cause |
|---|---|
| All scores 0.0 | Metric raised; set `provide_traceback=True`. |
| Optimization plateaus after 1-2 rounds | Metric feedback is generic/empty. Add specifics. |
| Eval takes forever | `num_threads=1`. Bump to 8–16 if the LM allows. |
| Scores non-deterministic between runs | Cache miss. Check `DSPY_CACHEDIR` and `dspy.LM(cache=True)`. |
| Baseline > optimized | Overfitting to trainset; use separate valset. |
