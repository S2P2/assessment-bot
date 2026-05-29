# DSPy Optimizers & Evaluation

*Includes content from [dspy-agent-skills](https://github.com/intertwine/dspy-agent-skills) v0.2.3 ([`f2f7055`](https://github.com/intertwine/dspy-agent-skills/commit/f2f7055770e8c28f755a652e4d507da813a17c8a)).*

## Optimizers (Teleprompters)

| Optimizer | Best For | Data Needed | Notes |
|-----------|----------|-------------|-------|
| `dspy.GEPA` | **Default recommendation (2026)**. Reflective/evolutionary. | 50+ examples | Rich-feedback metric required. See [gepa.md](gepa.md) for deep dive. |
| `dspy.MIPROv2` | Full prompt + demo optimization | 50-300 examples | Bayesian search over instructions + demos |
| `dspy.BetterTogether` | Multi-stage optimizer chains | 100+ examples | Chains arbitrary named optimizers. See [gepa.md](gepa.md). |
| `dspy.BootstrapFewShot` | Few-shot demos, fast | 5-50 examples | Low signal |
| `dspy.BootstrapFewShotWithRandomSearch` | Better few-shot selection | ~50-200 examples | |
| `dspy.COPRO` | Instruction-only optimization | 20-100 examples | |
| `dspy.SIMBA` | Mini-batch stochastic optimization | 20-200 examples | Lighter reflective optimizer |
| `dspy.KNNFewShot` | Dynamic example retrieval | Training set | |
| `dspy.Ensemble` | Combine multiple programs | Multiple programs | |
| `dspy.BootstrapFinetune` | Fine-tuning LM weights | 100+ examples | |
| `dspy.ArborGRPO` | Reinforcement learning / GRPO | 100+ examples | `pip install arbor-ai`; multi-module RL |

## GEPA — quick reference

GEPA is the 2026 gold standard. See [gepa.md](gepa.md) for the full deep dive.

```python
optimizer = dspy.GEPA(
    metric=rich_metric,                    # must return dspy.Prediction(score=, feedback=)
    auto="medium",                         # "light" / "medium" / "heavy"
    reflection_lm=dspy.LM("openai/gpt-5", temperature=1.0, max_tokens=32000),
    candidate_selection_strategy="pareto",
    num_threads=8,
    track_stats=True,
    log_dir="./gepa_logs",
)
optimized = optimizer.compile(student=program, trainset=trainset, valset=valset)
optimized.save("optimized.json", save_program=False)
```

**GEPA critical notes:**
- Its metric must return `dspy.Prediction(score=float, feedback=str)`, NOT a dict.
- `reflection_lm` is required at construction time, not compile time.
- Always run `auto="light"` first as a sanity check.
- Maximize trainset size; keep valset separate but representative.
- See [evaluation.md](evaluation.md) for the rich-feedback metric pattern.

## BetterTogether (3.2.x)

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

Pass `strategy=` explicitly when using named stages. Default `"p -> w -> p"` assumes keys are literally `p` and `w`.

## MIPROv2 — standard optimization

```python
optimizer = dspy.MIPROv2(
    metric=my_metric,
    auto="medium",         # "light", "medium", or "heavy"
    num_threads=8,
)
optimized = optimizer.compile(
    my_program,
    trainset=trainset,
    max_bootstrapped_demos=3,
    max_labeled_demos=3,
    num_trials=30,
)
optimized.save("optimized.json")
```

## When to use which optimizer

| Scenario | Optimizer |
|---|---|
| Complex program, rich metric, moderate budget | **GEPA** |
| Large trainset, scalar metric, high budget | MIPROv2 |
| Quick few-shot extraction | BootstrapFewShot |
| Multi-stage: bootstrap then reflect | BetterTogether |
| Cheaper reflective pass | SIMBA |

## Evaluation

See [evaluation.md](evaluation.md) for the full evaluation harness guide.

```python
# Simple metric
def my_metric(example, pred, trace=None):
    return example.answer.lower() == pred.answer.lower()

# LLM-as-judge metric
class AssessQuality(dspy.Signature):
    """Assess if the answer is grounded in context and helpful."""
    context: str = dspy.InputField()
    answer: str = dspy.InputField()
    is_grounded: bool = dspy.OutputField(desc="Is the answer supported by context?")
    helpfulness: int = dspy.OutputField(desc="1-5 score")

judge = dspy.Predict(AssessQuality)

def custom_metric(example, pred, trace=None):
    assessment = judge(context=example.context, answer=pred.answer)
    score = 1.0 if assessment.is_grounded else 0.0
    score += (assessment.helpfulness / 5.0)
    return score / 2.0

# Run evaluation
evaluator = dspy.Evaluate(
    devset=devset,
    metric=my_metric,
    num_threads=8,
    display_progress=True,
    display_table=5,
)
result = evaluator(my_program)  # returns EvaluationResult
print(result.score)

# Built-in metrics
dspy.evaluate.answer_exact_match      # exact string match
dspy.evaluate.answer_passage_match    # answer appears in passage
dspy.SemanticF1()                     # LM-based semantic F1 score
dspy.CompleteAndGrounded()            # checks completeness and grounding
```
