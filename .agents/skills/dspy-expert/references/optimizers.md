# DSPy Optimizers & Evaluation

## Optimizers (Teleprompters)

| Optimizer | Best For | Data Needed | Notes |
|-----------|----------|-------------|-------|
| `BootstrapFewShot` | Few-shot demos, fast | 5-50 examples | |
| `BootstrapFewShotWithRandomSearch` | Better few-shot selection | ~50-200 examples | |
| `MIPROv2` | Full prompt + demo optimization | 50-300 examples | **Default recommendation** |
| `COPRO` | Instruction-only optimization | 20-100 examples | |
| `SIMBA` | Mini-batch stochastic optimization | 20-200 examples | Faster for large programs |
| `GEPA` | Evolutionary prompt optimization | 50+ examples | 5-arg metric required |
| `BetterTogether` | Prompt + weight joint optimization | 100+ examples | Requires `experimental=True` |
| `KNNFewShot` | Dynamic example retrieval | Training set | |
| `Ensemble` | Combine multiple programs | Multiple programs | |
| `BootstrapFinetune` | Fine-tuning LM weights | 100+ examples | Requires `experimental=True` |
| `ArborGRPO` | Reinforcement learning / GRPO | 100+ examples | `pip install arbor-ai`; multi-module RL |

**GEPA critical note — its metric must accept 5 arguments:**
```python
def gepa_metric(gold, pred, trace, pred_name, pred_trace):
    return gold.answer.lower() == pred.answer.lower()
optimizer = dspy.GEPA(metric=gepa_metric, auto="medium", reflection_lm=dspy.LM('openai/gpt-4o'))
```

**BetterTogether (experimental) — combines prompt + weight optimization:**
```python
dspy.settings.experimental = True
from dspy.teleprompt import BetterTogether
optimizer = BetterTogether(metric=my_metric)
optimized = optimizer.compile(program, trainset=trainset, strategy="p -> w -> p")
```
```python
# Standard optimization pattern
optimizer = dspy.MIPROv2(
    metric=my_metric, 
    auto="medium", # "light", "medium", or "heavy"
    num_threads=8,
)
optimized = optimizer.compile(
    my_program, 
    trainset=trainset,
    max_bootstrapped_demos=3,
    max_labeled_demos=3,
    num_trials=30, # can override the auto setting
)
optimized.save("optimized.json")
```

---

## Evaluation

```python
# Simple logic metric
def my_metric(example, pred, trace=None):
    return example.answer.lower() == pred.answer.lower()

# LLM-as-a-judge metric (Advanced)
class AssessQuality(dspy.Signature):
    """Assess if the answer is grounded in context and helpful."""
    context: str = dspy.InputField()
    answer: str = dspy.InputField()
    is_grounded: bool = dspy.OutputField(desc="Is the answer supported by context?")
    helpfulness: int = dspy.OutputField(desc="1-5 score")

judge = dspy.Predict(AssessQuality)
# Using dspy.Predict with a typed signature (Pydantic or Literal)
# handles structured assessment results.
```
def custom_metric(example, pred, trace=None):
    assessment = judge(context=example.context, answer=pred.answer)
    score = 1.0 if assessment.is_grounded else 0.0
    score += (assessment.helpfulness / 5.0)
    return score / 2.0 # Normalized to 0-1
```

```python
# Run evaluation
...

evaluator = dspy.Evaluate(
    devset=devset,
    metric=my_metric,
    num_threads=8,
    display_progress=True,
    display_table=5,
)
score = evaluator(my_program)  # returns EvaluationResult

# Built-in metrics
dspy.evaluate.answer_exact_match      # exact string match
dspy.evaluate.answer_passage_match    # answer appears in passage
dspy.SemanticF1()                     # LM-based semantic F1 score
dspy.CompleteAndGrounded()            # checks if answer is complete and grounded in context
```
