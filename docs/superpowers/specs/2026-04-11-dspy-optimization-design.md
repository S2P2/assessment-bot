# DSPy Optimization Design

**Date:** 2026-04-11
**Status:** Draft
**Target model:** gemma4:26b (replacing qwen3.5:4b)

## Summary

Add DSPy optimization (BootstrapFewShot, then MIPROv2) to improve interview evaluation quality. This requires a schema refactoring to simplify the LLM's output and make optimization more effective, followed by a progressive optimization pipeline using hand-crafted SQL training data.

## Goals

1. Improve evaluation quality (correct/incorrect/partially_correct/ambiguous accuracy)
2. Learn DSPy optimization techniques (BootstrapFewShot, MIPROv2)
3. Build a reusable optimization pipeline for future question sets

## Non-goals

- Expanding question topics beyond SQL (future work)
- Scoring/grading system
- Admin dashboard
- Database-backed sessions
- Synthetic data generation
- LLM-as-judge metric (use exact match for now)
- Merging web.py and main.py

## Phase 0: Schema Refactoring

Remove the `command` field from LLM output. The orchestrator derives its behavior directly from the evaluation result.

### New evaluation model

| Evaluation | Meaning | Orchestrator behavior |
|---|---|---|
| `correct` | Fully meets criteria | Advance to next question |
| `partially_correct` | On the right track but incomplete | No penalty, ask to elaborate |
| `incorrect` | Doesn't meet criteria or has errors | Increment hints; force-skip if max reached |
| `ambiguous` | Too vague to evaluate | No penalty, ask for clarification |

Rules:
- `correct` always advances. No probing after a correct answer.
- `partially_correct` increments `hints_given`. Force-skip when `hints_given >= max_hints`.
- `incorrect` increments `hints_given`. Force-skip when `hints_given >= max_hints`.
- `ambiguous` does not increment hints (no penalty).

### Changes

**`src/schema.py`:**
- Remove `command` field from `InterviewAction`
- Expand `evaluation` to include `partially_correct`
- Add response-style guidance to each evaluation's description

```python
class InterviewAction(BaseModel):
    evaluation: Literal["correct", "partially_correct", "incorrect", "ambiguous"] = Field(
        description=(
            "correct: fully meets criteria. Response must be a concluding statement with no follow-ups. "
            "partially_correct: on the right track but incomplete, nothing wrong. Response should ask them to elaborate on the missing parts. "
            "incorrect: doesn't meet criteria or has errors. Response should guide with a hint. "
            "ambiguous: too vague to evaluate. Response should ask for clarification."
        )
    )
    reasoning: str = Field(description="Internal logic for the evaluation")
    response: str = Field(description="The message for the candidate")
```

**`src/signatures.py`:**
- Remove command-related guidance from the `action` output field description
- Update to reflect evaluation-driven flow

**`src/orchestrator.py`:**
- Remove `attempts` field (use existing `hints_given` for force-skip logic)
- Rename `max_attempts` to `max_hints`
- `record_turn(evaluation)` replaces `record_turn(command, evaluation)`
- Internal `_advance_question()` helper for question transition + summary
- Remove `should_force_skip()` — inline the check in `record_turn()`

```python
def record_turn(self, evaluation):
    self.last_evaluation = evaluation
    self.evaluation_history.append(evaluation)
    self.turns_in_question += 1

    if evaluation == "correct":
        self._advance_question(evaluation)
    elif evaluation == "partially_correct":
        self.hints_given += 1
        if self.hints_given >= self.max_hints:
            self._advance_question(evaluation, force_skip=True)
    elif evaluation == "incorrect":
        self.hints_given += 1
        if self.hints_given >= self.max_hints:
            self._advance_question(evaluation, force_skip=True)
    elif evaluation == "ambiguous":
        pass  # CLARIFY — no penalty

def _advance_question(self, evaluation, force_skip=False):
    """Record summary and advance to the next question."""
    q = self.get_current_question()
    summary = {
        "question_id": q.get("id"),
        "final_evaluation": evaluation,
        "total_turns": self.turns_in_question,
        "hints_used": self.hints_given,
        "clarifications_used": self.clarifications_requested,
        "was_force_skipped": force_skip,
    }
    self.question_summaries.append(summary)
    self.current_idx += 1
    self.turns_in_question = 0
    self.hints_given = 0
    self.clarifications_requested = 0
    self.evaluation_history = []
```

Note: `partially_correct` increments `hints_given` because the interviewer is spending a turn on probing — repeated probes without progress should eventually force-skip, same as repeated incorrect answers.

**`web.py`:**
- Remove `action.command` usage
- Use `evaluation` directly for orchestrator flow
- Remove `should_force_skip()` override (now handled inside `record_turn()`)

**`main.py`:**
- Remove `action.command` usage
- Use `evaluation` directly for orchestrator flow

**`tests/`:**
- Update all tests for new `record_turn(evaluation)` API
- Update tests that check `max_attempts` to use `max_hints`
- Update schema tests for new evaluation types
- Remove tests for `command` field

## Phase 1: Training Data

### File layout

```
data/training/sql_examples.json   # ~20 hand-crafted examples
src/training.py                   # Loads data, converts to dspy.Example
```

### Example format

```json
{
  "topic": "SQL Basics",
  "question": "How do you find unique values in a column?",
  "criteria": "Must use the DISTINCT keyword.",
  "hint_guidelines": "Nudge toward uniqueness without saying 'DISTINCT'.",
  "history": [],
  "user_input": "You can use SELECT UNIQUE from the column",
  "attempt_number": 0,
  "last_evaluation": "None",
  "next_topic": "SQL Basics",
  "action": {
    "evaluation": "incorrect",
    "reasoning": "UNIQUE is Oracle-specific; DISTINCT is standard SQL.",
    "response": "Close! There's a more standard SQL keyword for this. Try again?"
  }
}
```

### Coverage

| Category | Count | Scenarios |
|---|---|---|
| correct | 5 | Direct correct, detailed correct, concise correct |
| partially_correct | 5 | Missing key detail, right concept incomplete |
| incorrect | 5 | Wrong concept, wrong syntax, misconception |
| ambiguous | 5 | Vague, "it depends", one-word answer |

### `src/training.py`

- `load_training_data(path)` — loads JSON, validates, returns list of dicts
- `to_examples(data)` — converts to `dspy.Example` objects with `.with_inputs()` marking all signature input fields

## Phase 2: BootstrapFewShot Baseline

### New file: `scripts/optimize.py`

```python
optimizer = dspy.BootstrapFewShot(
    metric=evaluation_accuracy,
    max_bootstrapped_demos=4,
    max_labeled_demos=4,
)
compiled = optimizer.compile(InterviewBot(), trainset=trainset)
compiled.save("models/bootstrap_fewshot.json")
```

### Metric: exact evaluation match

```python
def evaluation_accuracy(example, prediction, trace=None):
    """Score 1.0 if evaluation matches the gold label."""
    return 1.0 if example.action.evaluation == prediction.action.evaluation else 0.0
```

### Output

- `models/bootstrap_fewshot.json` — compiled model with few-shot demonstrations
- Comparison: run both compiled and uncompiled against held-out test examples

## Phase 3: MIPROv2 Optimization

```python
optimizer = dspy.MIPROv2(
    metric=evaluation_accuracy,
    auto="medium",
)
compiled = optimizer.compile(
    InterviewBot(),
    trainset=trainset,
    max_bootstrapped_demos=4,
    max_labeled_demos=4,
)
compiled.save("models/miprov2.json")
```

MIPROv2 optimizes both prompt instructions and demonstration selection. Compare against BootstrapFewShot baseline on held-out data.

## Integration

- `src/modules.py`: `InterviewBot` loads compiled model if `models/miprov2.json` (or bootstrap) exists
- `web.py` and `main.py`: no changes needed — they call `bot()` the same way

## Future Work (Phase 4+)

- **Data mining pipeline**: Extract Q&A pairs from MLflow traces and session files for relabeling. MLflow has a built-in evaluation/labeling UI.
- **Expanded question set**: More SQL questions, then Python, networking, etc.
- **Softer metric**: Weighted metric that partially credits close evaluations or uses an LLM-as-judge for response quality.
- **Continuous optimization**: Re-optimize as more labeled data accumulates.

## File Change Summary

| File | Phase | Change |
|---|---|---|
| `src/schema.py` | 0 | Remove command, add partially_correct, update descriptions |
| `src/signatures.py` | 0 | Remove command guidance |
| `src/orchestrator.py` | 0 | Evaluation-driven record_turn, drop attempts, rename max_hints |
| `web.py` | 0 | Use evaluation instead of command |
| `main.py` | 0 | Use evaluation instead of command |
| `tests/*.py` | 0 | Update all tests for new API |
| `data/training/sql_examples.json` | 1 | New: training examples |
| `src/training.py` | 1 | New: training data loader |
| `scripts/optimize.py` | 2-3 | New: optimization runner |
