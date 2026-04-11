# DSPy Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the evaluation schema (remove command, add partially_correct) and build a progressive DSPy optimization pipeline (BootstrapFewShot, then MIPROv2).

**Architecture:** Remove the `command` field from `InterviewAction` so the LLM only decides the evaluation. The orchestrator derives its behavior directly from the evaluation result. Then create hand-crafted SQL training data and run DSPy optimizers to improve evaluation accuracy.

**Tech Stack:** DSPy 3.1.3, Pydantic, Gradio 6, MLflow

---

### Task 1: Update InterviewAction schema

**Files:**
- Modify: `src/schema.py:1-13`
- Modify: `tests/test_schema.py:1-63`

- [ ] **Step 1: Write the failing tests for the new schema**

Replace the entire content of `tests/test_schema.py`:

```python
import pytest
from pydantic import ValidationError
from src.schema import InterviewAction


def test_interview_action_correct():
    action = InterviewAction(
        evaluation="correct",
        reasoning="User got it right.",
        response="Great job!",
    )
    assert action.evaluation == "correct"


def test_interview_action_partially_correct():
    action = InterviewAction(
        evaluation="partially_correct",
        reasoning="Right concept but missing key detail.",
        response="You're on the right track. Can you elaborate?",
    )
    assert action.evaluation == "partially_correct"


def test_interview_action_incorrect():
    action = InterviewAction(
        evaluation="incorrect",
        reasoning="Missing key concept.",
        response="Not quite.",
    )
    assert action.evaluation == "incorrect"


def test_interview_action_ambiguous():
    action = InterviewAction(
        evaluation="ambiguous",
        reasoning="Answer was vague.",
        response="Can you elaborate?",
    )
    assert action.evaluation == "ambiguous"


def test_interview_action_invalid_evaluation():
    with pytest.raises(ValidationError):
        InterviewAction(
            evaluation="excellent",
            reasoning="N/A",
            response="N/A",
        )


def test_interview_action_command_field_removed():
    """Command field no longer exists on InterviewAction."""
    with pytest.raises(ValidationError):
        InterviewAction(
            evaluation="correct",
            reasoning="N/A",
            response="N/A",
            command="NEXT_QUESTION",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/test_schema.py -v`
Expected: FAIL — `InterviewAction` still accepts `command` and doesn't accept `partially_correct`

- [ ] **Step 3: Update the schema**

Replace the entire content of `src/schema.py`:

```python
from pydantic import BaseModel, Field
from typing import Literal


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

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/test_schema.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add src/schema.py tests/test_schema.py
git commit -m "refactor: remove command field, add partially_correct evaluation"
```

---

### Task 2: Update orchestrator to evaluation-driven model

**Files:**
- Modify: `src/orchestrator.py:1-59`
- Modify: `tests/test_orchestrator.py:1-101`

- [ ] **Step 1: Write the failing tests for the new orchestrator**

Replace the entire content of `tests/test_orchestrator.py`:

```python
from src.orchestrator import InterviewOrchestrator


def test_orchestrator_correct_advances():
    questions = [{"id": "q1", "text": "Q1"}, {"id": "q2", "text": "Q2"}]
    orc = InterviewOrchestrator(questions)
    assert orc.get_current_question()["id"] == "q1"
    orc.record_turn("correct")
    assert orc.get_current_question()["id"] == "q2"
    assert orc.hints_given == 0


def test_orchestrator_incorrect_increments_hints():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("incorrect")
    assert orc.hints_given == 1
    assert orc.current_idx == 0


def test_orchestrator_partially_correct_increments_hints():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("partially_correct")
    assert orc.hints_given == 1
    assert orc.current_idx == 0


def test_orchestrator_ambiguous_no_penalty():
    questions = [{"id": "q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.record_turn("ambiguous")
    assert orc.hints_given == 0
    assert orc.current_idx == 0
    assert orc.clarifications_requested == 1


def test_orchestrator_force_skip_on_incorrect():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("incorrect")
    assert orc.current_idx == 0
    orc.record_turn("incorrect")
    assert orc.current_idx == 1
    assert orc.question_summaries[0]["was_force_skipped"] is True


def test_orchestrator_force_skip_on_partially_correct():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}, {"id": "q2", "text": "Q2"}]
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("partially_correct")
    orc.record_turn("partially_correct")
    assert orc.current_idx == 1
    assert orc.question_summaries[0]["was_force_skipped"] is True


def test_orchestrator_get_next_topic_name():
    questions = [
        {"id": "q1", "text": "Q1", "topic_name": "Topic 1"},
        {"id": "q2", "text": "Q2", "topic_name": "Topic 2"},
    ]
    orc = InterviewOrchestrator(questions)
    assert orc.get_next_topic_name() == "Topic 2"
    orc.record_turn("correct")
    assert orc.get_next_topic_name() is None


def test_orchestrator_record_turn_tracks_state():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)

    # First turn: ambiguous (clarify)
    orc.record_turn("ambiguous")
    assert orc.turns_in_question == 1
    assert orc.clarifications_requested == 1
    assert orc.last_evaluation == "ambiguous"

    # Second turn: incorrect (hint)
    orc.record_turn("incorrect")
    assert orc.turns_in_question == 2
    assert orc.hints_given == 1

    # Third turn: correct (advance)
    orc.record_turn("correct")
    assert len(orc.question_summaries) == 1
    assert orc.question_summaries[0]["final_evaluation"] == "correct"
    assert orc.turns_in_question == 0  # Reset


def test_orchestrator_empty_questions():
    orc = InterviewOrchestrator([])
    assert orc.get_current_question() is None


def test_orchestrator_unknown_evaluation_no_op():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.record_turn("unknown_eval")
    assert orc.turns_in_question == 1
    assert orc.hints_given == 0
    assert orc.current_idx == 0


def test_orchestrator_max_hints_default():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions)
    assert orc.max_hints == 2


def test_get_next_topic_name_single_question():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "Only Topic"}]
    orc = InterviewOrchestrator(questions)
    assert orc.get_next_topic_name() is None


def test_orchestrator_summary_includes_all_fields():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.record_turn("ambiguous")
    orc.record_turn("incorrect")
    orc.record_turn("correct")
    summary = orc.question_summaries[0]
    assert summary["question_id"] == "q1"
    assert summary["final_evaluation"] == "correct"
    assert summary["total_turns"] == 3
    assert summary["hints_used"] == 1
    assert summary["clarifications_used"] == 1
    assert summary["was_force_skipped"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/test_orchestrator.py -v`
Expected: FAIL — `record_turn` still takes 2 args, `max_hints` doesn't exist

- [ ] **Step 3: Update the orchestrator**

Replace the entire content of `src/orchestrator.py`:

```python
class InterviewOrchestrator:
    def __init__(self, questions, max_hints=2):
        self.questions = questions
        self.current_idx = 0
        self.max_hints = max_hints
        self.history = []

        # Turn tracking
        self.turns_in_question = 0
        self.hints_given = 0
        self.clarifications_requested = 0
        self.last_evaluation = "None"
        self.evaluation_history = []
        self.question_summaries = []

    def get_current_question(self):
        if self.current_idx >= len(self.questions):
            return None
        return self.questions[self.current_idx]

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
            self.clarifications_requested += 1

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

    def get_next_topic_name(self):
        next_idx = self.current_idx + 1
        if next_idx >= len(self.questions):
            return None
        return self.questions[next_idx]["topic_name"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/test_orchestrator.py -v`
Expected: 13 PASS

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator.py tests/test_orchestrator.py
git commit -m "refactor: orchestrator uses evaluation-driven record_turn, drop attempts/max_attempts"
```

---

### Task 3: Update DSPy signature

**Files:**
- Modify: `src/signatures.py:1-21`

- [ ] **Step 1: Update the signature**

Replace the entire content of `src/signatures.py`:

```python
import dspy
from src.schema import InterviewAction


class InterviewTurn(dspy.Signature):
    """Evaluate candidate answer and generate the next interviewer response."""

    topic = dspy.InputField()
    question = dspy.InputField()
    criteria = dspy.InputField()
    hint_guidelines = dspy.InputField()
    history = dspy.InputField(desc="Previous turns as a list of strings")
    user_input = dspy.InputField()
    attempt_number = dspy.InputField()
    last_evaluation = dspy.InputField(
        desc="The evaluation result from the previous turn, or 'None' if first turn."
    )
    next_topic = dspy.InputField(desc="Name of the next topic, or None if finishing.")
    action: InterviewAction = dspy.OutputField(
        desc="Structured response with evaluation (correct/partially_correct/incorrect/ambiguous), reasoning, and the next response string."
    )
```

- [ ] **Step 2: Verify no import errors**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run python -c "from src.signatures import InterviewTurn; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/signatures.py
git commit -m "refactor: remove command guidance from InterviewTurn signature"
```

---

### Task 4: Update session serialization

**Files:**
- Modify: `src/session.py:128-165` (serialization functions)
- Modify: `tests/test_session.py:77,167` (record_turn calls)
- Modify: `tests/test_web.py:66-67,77,82,90-94,133,145,167,182` (record_turn calls)

- [ ] **Step 1: Update `_serialize_orchestrator` in `src/session.py`**

Replace the `_serialize_orchestrator` function (lines 128-141) with:

```python
def _serialize_orchestrator(orc: InterviewOrchestrator) -> dict:
    """Serialize orchestrator state. Excludes question data."""
    return {
        "current_idx": orc.current_idx,
        "max_hints": orc.max_hints,
        "turns_in_question": orc.turns_in_question,
        "hints_given": orc.hints_given,
        "clarifications_requested": orc.clarifications_requested,
        "last_evaluation": orc.last_evaluation,
        "history": orc.history,
        "evaluation_history": orc.evaluation_history,
        "question_summaries": orc.question_summaries,
    }
```

- [ ] **Step 2: Update `_deserialize_orchestrator` in `src/session.py`**

Replace the `_deserialize_orchestrator` function (lines 144-165) with:

```python
def _deserialize_orchestrator(
    state: dict,
    questions: list[dict],
) -> Optional[InterviewOrchestrator]:
    """Rebuild orchestrator from saved state + fresh questions."""
    try:
        orc = InterviewOrchestrator(
            questions,
            max_hints=state.get("max_hints", state.get("max_attempts", 2)),
        )
        orc.current_idx = state["current_idx"]
        orc.turns_in_question = state["turns_in_question"]
        orc.hints_given = state.get("hints_given", state.get("attempts", 0))
        orc.clarifications_requested = state["clarifications_requested"]
        orc.last_evaluation = state["last_evaluation"]
        orc.history = state["history"]
        orc.evaluation_history = state["evaluation_history"]
        orc.question_summaries = state["question_summaries"]
        return orc
    except (KeyError, TypeError, IndexError):
        return None
```

Note: `state.get("max_attempts", 2)` fallback supports deserializing old session files. Same for `state.get("attempts", 0)`.

- [ ] **Step 3: Update test_session.py — fix record_turn calls**

In `tests/test_session.py`, change line 77 from:
```python
data.orchestrator.record_turn("NEXT_QUESTION", "correct")
```
to:
```python
data.orchestrator.record_turn("correct")
```

Change line 167 from:
```python
data.orchestrator.record_turn("GIVE_HINT", "incorrect")
```
to:
```python
data.orchestrator.record_turn("incorrect")
```

Change line 182 from:
```python
assert resumed.orchestrator.attempts == 1
```
to:
```python
assert resumed.orchestrator.hints_given == 1
```

- [ ] **Step 4: Update test_web.py — fix record_turn calls**

In `tests/test_web.py`, change all `record_turn` calls:

Line 66: `orc.record_turn("NEXT_QUESTION", "correct")` → `orc.record_turn("correct")`
Line 67: `orc.record_turn("NEXT_QUESTION", "correct")` → `orc.record_turn("correct")`
Line 77: `orc.record_turn("NEXT_QUESTION", "correct")` → `orc.record_turn("correct")`
Line 82: `orc.record_turn("NEXT_QUESTION", "correct")` → `orc.record_turn("correct")`

Lines 90-94: Replace the entire `test_build_history_skipped` function:
```python
def test_build_history_skipped():
    questions = _sample_questions()
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("incorrect")
    orc.record_turn("incorrect")
    assert orc.current_idx == 1  # force-skipped
    result = _build_history(orc)
    assert "skipped" in result
    assert result.startswith("-")
```

Line 133: `orc.record_turn("NEXT_QUESTION", "correct")` → `orc.record_turn("correct")`
Line 145: `orc.record_turn("NEXT_QUESTION", "correct")` → `orc.record_turn("correct")`
Line 167: `orc.record_turn("GIVE_HINT", "incorrect")` → `orc.record_turn("incorrect")`
Line 182: `assert resumed.orchestrator.attempts == 1` → `assert resumed.orchestrator.hints_given == 1`

- [ ] **Step 5: Run all tests to verify**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/test_session.py tests/test_web.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/session.py tests/test_session.py tests/test_web.py
git commit -m "refactor: update session serialization for new orchestrator API"
```

---

### Task 5: Update web.py

**Files:**
- Modify: `web.py` (multiple locations)

- [ ] **Step 1: Update `_BADGE_MAP` (line 16-20)**

Add `partially_correct` entry. Change:
```python
_BADGE_MAP = {
    "correct": "\u2713",
    "incorrect": "\u2717",
    "ambiguous": "~",
}
```
to:
```python
_BADGE_MAP = {
    "correct": "\u2713",
    "partially_correct": "\u2248",
    "incorrect": "\u2717",
    "ambiguous": "~",
}
```

- [ ] **Step 2: Update `_build_sidebar` (line 75)**

Change `orc.attempts` / `orc.max_attempts` references. Replace line 75:
```python
f"**Attempts:** {orc.attempts} / {orc.max_attempts}",
```
with:
```python
f"**Hints:** {orc.hints_given} / {orc.max_hints}",
```

- [ ] **Step 3: Update `_call_bot_with_retry` (line 48)**

Change `attempt_number=orc.attempts` to `attempt_number=orc.hints_given`. Replace line 48:
```python
attempt_number=orc.attempts,
```
with:
```python
attempt_number=orc.hints_given,
```

- [ ] **Step 4: Update `process_response` — MLflow span inputs (line 275)**

Change `attempt_number: orc.attempts` to `attempt_number: orc.hints_given`. Replace line 275:
```python
"attempt_number": orc.attempts,
```
with:
```python
"attempt_number": orc.hints_given,
```

- [ ] **Step 5: Update `process_response` — remove command logic (lines 299-339)**

Replace lines 299-339:
```python
            action = result.action
            command = action.command

            # Orchestrator override
            if orc.should_force_skip() and command == "GIVE_HINT":
                command = "PROMPT_SKIP"

            # Record turn
            orc.history.append(f"User: {user_message}")
            orc.history.append(f"Interviewer: {action.response}")
            orc.record_turn(command, action.evaluation)

            # Save session
            save_session(session_uuid)

            # Build response
            history.append({"role": "assistant", "content": action.response})

            # Check if interview complete
            next_q = orc.get_current_question()
            if next_q is None:
                summary_lines = ["---\n**Interview Complete!**\n"]
                for s in orc.question_summaries:
                    badge = _BADGE_MAP.get(s["final_evaluation"], "?")
                    summary_lines.append(
                        f"{badge} {s['question_id']}: {s['final_evaluation']}"
                    )
                history.append(
                    {
                        "role": "assistant",
                        "content": "\n".join(summary_lines),
                    }
                )
            elif command in ("NEXT_QUESTION", "PROMPT_SKIP"):
                # Show next question
                history.append(
                    {
                        "role": "assistant",
                        "content": f"[{next_q['topic_name']}] {next_q['text']}",
                    }
                )
```

with:
```python
            action = result.action
            evaluation = action.evaluation

            # Record turn (force-skip handled inside record_turn)
            orc.history.append(f"User: {user_message}")
            orc.history.append(f"Interviewer: {action.response}")
            orc.record_turn(evaluation)

            # Save session
            save_session(session_uuid)

            # Build response
            history.append({"role": "assistant", "content": action.response})

            # Check if question advanced (correct or force-skip)
            advanced = evaluation == "correct" or (
                orc.question_summaries
                and orc.question_summaries[-1].get("was_force_skipped")
            )
            next_q = orc.get_current_question()
            if next_q is None:
                summary_lines = ["---\n**Interview Complete!**\n"]
                for s in orc.question_summaries:
                    badge = _BADGE_MAP.get(s["final_evaluation"], "?")
                    summary_lines.append(
                        f"{badge} {s['question_id']}: {s['final_evaluation']}"
                    )
                history.append(
                    {
                        "role": "assistant",
                        "content": "\n".join(summary_lines),
                    }
                )
            elif advanced:
                # Show next question after correct answer or force-skip
                history.append(
                    {
                        "role": "assistant",
                        "content": f"[{next_q['topic_name']}] {next_q['text']}",
                    }
                )
```

- [ ] **Step 6: Run all tests to verify**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/ -v`
Expected: All tests PASS (some test_web.py sidebar tests may need minor fixes for "Hints" label)

- [ ] **Step 7: Fix any failing test assertions for label changes**

In `tests/test_web.py`, update `test_build_sidebar_active_question` line 60:
```python
assert "0 / 2" in attempts
```
This should still pass since `max_hints` defaults to 2. Verify.

- [ ] **Step 8: Commit**

```bash
git add web.py
git commit -m "refactor: web.py uses evaluation-driven orchestrator, remove command logic"
```

---

### Task 6: Update main.py

**Files:**
- Modify: `main.py` (multiple locations)

- [ ] **Step 1: Update `_call_bot_with_retry` (line 136)**

Change `attempt_number=orc.attempts` to `attempt_number=orc.hints_given`. Replace line 136:
```python
attempt_number=orc.attempts,
```
with:
```python
attempt_number=orc.hints_given,
```

- [ ] **Step 2: Update MLflow span inputs (line 89)**

Change `attempt_number: orc.attempts` to `attempt_number: orc.hints_given`. Replace line 89:
```python
"attempt_number": orc.attempts,
```
with:
```python
"attempt_number": orc.hints_given,
```

- [ ] **Step 3: Remove command logic and update record_turn (lines 106-118)**

Replace lines 106-118:
```python
            action = result.action
            command = action.command

            # Orchestrator Override
            if orc.should_force_skip() and command == "GIVE_HINT":
                command = "PROMPT_SKIP"
                print("\n(System: Maximum attempts reached. Suggesting skip.)")

            print(f"\nInterviewer: {action.response}")

            orc.history.append(f"User: {user_input}")
            orc.history.append(f"Interviewer: {action.response}")
            orc.record_turn(command, action.evaluation)
```

with:
```python
            action = result.action
            evaluation = action.evaluation

            print(f"\nInterviewer: {action.response}")

            orc.history.append(f"User: {user_input}")
            orc.history.append(f"Interviewer: {action.response}")
            orc.record_turn(evaluation)
```

- [ ] **Step 4: Run all tests to verify**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/ -v`
Expected: All PASS

- [ ] **Step 5: Run linter**

Run: `uv run ruff check src/ tests/ web.py main.py`
Expected: All checks passed

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "refactor: main.py uses evaluation-driven orchestrator, remove command logic"
```

---

### Task 7: Full test suite verification

**Files:**
- All modified files

- [ ] **Step 1: Run the full test suite**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run linter on all files**

Run: `uv run ruff check src/ tests/ web.py main.py`
Expected: All checks passed

- [ ] **Step 3: Run formatter check**

Run: `uv run ruff format --check src/ tests/ web.py main.py`
Expected: All files formatted

- [ ] **Step 4: Bump version**

In `pyproject.toml`, change `version = "0.4.0"` to `version = "0.5.0"`.

In `web.py`, change `VERSION = "0.4.1"` to `VERSION = "0.5.0"`.

- [ ] **Step 5: Update CLAUDE.md**

In `CLAUDE.md`, update the Project Structure section to add the new files:

```markdown
## Project Structure

- `questions.json` — interview question data (validated against `schemas/questions.schema.json`)
- `src/data.py` — loads and flattens questions with schema validation
- `src/orchestrator.py` — interview state machine (evaluation-driven)
- `src/modules.py` / `src/signatures.py` — DSPy interview bot
- `src/schema.py` — Pydantic models for LLM output
- `src/session.py` — JSON file-based session persistence
- `src/config.py` — shared config loading and LLM initialization
- `main.py` — CLI entry point
- `web.py` — Gradio 6 web UI
```

- [ ] **Step 6: Commit version bump**

```bash
git add pyproject.toml web.py CLAUDE.md
git commit -m "chore: bump version to 0.5.0 for evaluation-driven refactor"
```

---

### Task 8: Create SQL training data

**Files:**
- Create: `data/training/sql_examples.json`

- [ ] **Step 1: Create the training data directory**

Run: `mkdir -p data/training`

- [ ] **Step 2: Write the training examples**

Create `data/training/sql_examples.json` with 20 examples across the 4 evaluation categories, based on the 2 SQL questions in `questions.json`:

```json
[
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "You can use SELECT DISTINCT column_name FROM table_name to get only the unique values.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "correct",
      "reasoning": "User correctly identified SELECT DISTINCT as the way to find unique values.",
      "response": "Excellent! SELECT DISTINCT is exactly right for retrieving unique values from a column."
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "I think you use DISTINCT somehow, like SELECT DISTINCT FROM table.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "correct",
      "reasoning": "User mentioned DISTINCT, which is the required keyword. Syntax is slightly off but the concept is correct.",
      "response": "That's right! DISTINCT is the keyword. You'd specify the column name: SELECT DISTINCT column_name FROM table_name."
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "You can use GROUP BY on that column to get unique values.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "correct",
      "reasoning": "While GROUP BY can produce unique values, the expected answer is DISTINCT. However, GROUP BY is a valid SQL approach to finding unique values.",
      "response": "GROUP BY can work for that purpose! The most direct keyword for this is DISTINCT though. Good alternative thinking."
    }
  },
  {
    "topic": "SQL Basics",
    "question": "What is the difference between an INNER JOIN and a LEFT JOIN?",
    "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
    "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second.",
    "history": [],
    "user_input": "INNER JOIN only returns rows where there's a match in both tables. LEFT JOIN returns all rows from the left table, and matching rows from the right table — if no match, you get NULLs.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "Python Basics",
    "action": {
      "evaluation": "correct",
      "reasoning": "User correctly explained both INNER JOIN (matching rows only) and LEFT JOIN (all left rows, NULLs for non-matches).",
      "response": "Perfect explanation! You nailed both the matching-only behavior of INNER JOIN and the NULL-filling behavior of LEFT JOIN."
    }
  },
  {
    "topic": "SQL Basics",
    "question": "What is the difference between an INNER JOIN and a LEFT JOIN?",
    "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
    "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second.",
    "history": [],
    "user_input": "INNER JOIN gives you matching rows. LEFT JOIN gives you everything from the left table plus matches.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "Python Basics",
    "action": {
      "evaluation": "correct",
      "reasoning": "User captured both key concepts: INNER JOIN = matching rows, LEFT JOIN = all left rows + matches.",
      "response": "That's the key distinction! INNER JOIN filters to matches only, while LEFT JOIN preserves all rows from the left table."
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "You can filter out duplicates somehow, I think there's a keyword for that.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "partially_correct",
      "reasoning": "User understands the concept of removing duplicates and knows there's a keyword, but hasn't named DISTINCT.",
      "response": "You're on the right track — there is indeed a keyword for filtering duplicates. Can you recall what it's called?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": ["User: You filter out duplicates", "Interviewer: Right concept. What's the keyword?"],
    "user_input": "Is it UNIQUE? Or maybe REMOVE DUPLICATES?",
    "attempt_number": 1,
    "last_evaluation": "partially_correct",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "partially_correct",
      "reasoning": "User is still guessing keywords close to DISTINCT but hasn't landed on it. UNIQUE is Oracle-specific, not standard SQL.",
      "response": "Very close! Think about the word that means 'different from each other' — it starts with 'D'."
    }
  },
  {
    "topic": "SQL Basics",
    "question": "What is the difference between an INNER JOIN and a LEFT JOIN?",
    "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
    "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second.",
    "history": [],
    "user_input": "INNER JOIN matches things, LEFT JOIN keeps the left side.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "Python Basics",
    "action": {
      "evaluation": "partially_correct",
      "reasoning": "User has the basic idea for both but lacks the key detail about what happens to non-matching rows in LEFT JOIN (NULLs).",
      "response": "You have the general idea! Can you be more specific about what LEFT JOIN does when there's no match on the right side?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "What is the difference between an INNER JOIN and a LEFT JOIN?",
    "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
    "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second.",
    "history": ["User: INNER JOIN matches things, LEFT JOIN keeps the left side.", "Interviewer: Can you be more specific about what happens when there's no match?"],
    "user_input": "If there's no match, LEFT JOIN shows the left row with empty values for the right side.",
    "attempt_number": 1,
    "last_evaluation": "partially_correct",
    "next_topic": "Python Basics",
    "action": {
      "evaluation": "partially_correct",
      "reasoning": "User now understands the NULL/empty behavior but hasn't explicitly stated that INNER JOIN returns only matching rows. Getting closer.",
      "response": "Good — those empty values are NULLs. And to confirm: what does INNER JOIN do differently?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "I don't really know, maybe ORDER BY?",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "partially_correct",
      "reasoning": "User is uncertain and ORDER BY is not the right keyword, but they're thinking about SQL operations on columns.",
      "response": "ORDER BY sorts results but doesn't remove duplicates. Think about a keyword that means 'different' or 'unique' — it goes right after SELECT."
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "You just do a normal SELECT and it gives you everything.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "incorrect",
      "reasoning": "User doesn't know how to filter for unique values. A plain SELECT returns all rows including duplicates.",
      "response": "A plain SELECT does return all rows, including duplicates. There's a specific keyword you can add to SELECT to filter those out. Can you think of it?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "You use the WHERE clause with a special condition.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "incorrect",
      "reasoning": "WHERE filters rows by condition but doesn't remove duplicates. This is the wrong approach.",
      "response": "WHERE filters rows based on conditions, but it won't help with duplicates. There's a keyword that goes between SELECT and the column name. Any ideas?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": ["User: You just do a normal SELECT", "Interviewer: There's a keyword that filters duplicates."],
    "user_input": "Is it HAVING?",
    "attempt_number": 1,
    "last_evaluation": "incorrect",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "incorrect",
      "reasoning": "HAVING is for filtering aggregate groups, not for removing duplicates. Still wrong.",
      "response": "HAVING is used for filtering groups after GROUP BY, not for removing duplicates. The keyword starts with 'D' and means 'different'."
    }
  },
  {
    "topic": "SQL Basics",
    "question": "What is the difference between an INNER JOIN and a LEFT JOIN?",
    "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
    "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second.",
    "history": [],
    "user_input": "They're basically the same thing, just written differently.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "Python Basics",
    "action": {
      "evaluation": "incorrect",
      "reasoning": "User claims INNER JOIN and LEFT JOIN are the same, which is fundamentally wrong.",
      "response": "They actually produce very different results! Think about what happens to rows in one table that don't have a match in the other table. What does each JOIN type do with those?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "What is the difference between an INNER JOIN and a LEFT JOIN?",
    "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
    "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second.",
    "history": ["User: They're the same thing.", "Interviewer: They produce different results! Think about unmatched rows."],
    "user_input": "LEFT JOIN shows the left table even without matches?",
    "attempt_number": 1,
    "last_evaluation": "incorrect",
    "next_topic": "Python Basics",
    "action": {
      "evaluation": "incorrect",
      "reasoning": "User now has a partial idea about LEFT JOIN but still hasn't explained INNER JOIN's behavior or the NULL concept for LEFT JOIN.",
      "response": "Yes, that's part of it! LEFT JOIN keeps all left table rows. And what does INNER JOIN do when there's no match? What values appear on the right side in a LEFT JOIN when there's no match?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "Um, I'm not sure. Something with SELECT?",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "ambiguous",
      "reasoning": "User mentions SELECT but is too vague to evaluate — doesn't address unique values at all.",
      "response": "You're on the right track that SELECT is involved. Can you be more specific about how you'd remove duplicate values from the results?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "It depends on the database.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "ambiguous",
      "reasoning": "User gives a non-answer. While technically different databases have quirks, DISTINCT is standard SQL and the question has a clear answer.",
      "response": "While databases do have some differences, there's a standard SQL keyword for this that works across most databases. Can you try to recall it?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "What is the difference between an INNER JOIN and a LEFT JOIN?",
    "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
    "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second.",
    "history": [],
    "user_input": "Joins connect tables.",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "Python Basics",
    "action": {
      "evaluation": "ambiguous",
      "reasoning": "User states a true but trivial fact. Doesn't address the difference between the two join types.",
      "response": "That's true, but the question asks about the difference between the two types. What happens to rows that don't have a match in the other table?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "What is the difference between an INNER JOIN and a LEFT JOIN?",
    "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
    "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second.",
    "history": ["User: Joins connect tables.", "Interviewer: What happens to rows without matches?"],
    "user_input": "I think one of them drops stuff and the other keeps it?",
    "attempt_number": 1,
    "last_evaluation": "ambiguous",
    "next_topic": "Python Basics",
    "action": {
      "evaluation": "ambiguous",
      "reasoning": "User is vaguely on the right track but too imprecise. 'Drops stuff' and 'keeps it' don't specify which join does what or what 'stuff' means.",
      "response": "You're thinking in the right direction! Can you be more specific: which one drops rows, which one keeps them, and what appears in place of missing data?"
    }
  },
  {
    "topic": "SQL Basics",
    "question": "How do you find unique values in a column?",
    "criteria": "Must use the DISTINCT keyword.",
    "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly.",
    "history": [],
    "user_input": "duplicates",
    "attempt_number": 0,
    "last_evaluation": "None",
    "next_topic": "SQL Basics",
    "action": {
      "evaluation": "ambiguous",
      "reasoning": "Single word answer. User may know the concept but hasn't demonstrated they know how to remove duplicates in SQL.",
      "response": "You're thinking about duplicates — that's relevant! But can you explain how you'd actually write the SQL query to remove them?"
    }
  }
]
```

- [ ] **Step 3: Validate the JSON**

Run: `uv run python -c "import json; data=json.load(open('data/training/sql_examples.json')); print(f'{len(data)} examples loaded'); cats={d['action']['evaluation'] for d in data}; print(f'Categories: {sorted(cats)}')"`
Expected: `20 examples loaded` and `Categories: ['ambiguous', 'correct', 'incorrect', 'partially_correct']`

- [ ] **Step 4: Commit**

```bash
git add data/training/sql_examples.json
git commit -m "data: add 20 SQL training examples for DSPy optimization"
```

---

### Task 9: Create training data loader

**Files:**
- Create: `src/training.py`
- Create: `tests/test_training.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_training.py`:

```python
import json
import pytest
from src.training import load_training_data, to_examples


def test_load_training_data(tmp_path):
    data = [
        {
            "topic": "SQL",
            "question": "Q1",
            "criteria": "c1",
            "hint_guidelines": "h1",
            "history": [],
            "user_input": "answer",
            "attempt_number": 0,
            "last_evaluation": "None",
            "next_topic": "SQL",
            "action": {
                "evaluation": "correct",
                "reasoning": "Right",
                "response": "Good!",
            },
        }
    ]
    path = tmp_path / "train.json"
    path.write_text(json.dumps(data))

    result = load_training_data(str(path))
    assert len(result) == 1
    assert result[0]["action"]["evaluation"] == "correct"


def test_load_training_data_missing_file():
    with pytest.raises(FileNotFoundError):
        load_training_data("nonexistent.json")


def test_load_training_data_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{invalid}")
    with pytest.raises(json.JSONDecodeError):
        load_training_data(str(path))


def test_to_examples():
    data = [
        {
            "topic": "SQL",
            "question": "Q1",
            "criteria": "c1",
            "hint_guidelines": "h1",
            "history": [],
            "user_input": "answer",
            "attempt_number": 0,
            "last_evaluation": "None",
            "next_topic": "SQL",
            "action": {
                "evaluation": "correct",
                "reasoning": "Right",
                "response": "Good!",
            },
        }
    ]
    examples = to_examples(data)
    assert len(examples) == 1

    # Verify inputs are marked correctly
    inputs = examples[0].inputs()
    assert hasattr(inputs, "topic")
    assert hasattr(inputs, "question")
    assert hasattr(inputs, "criteria")

    # Verify labels contain the action
    labels = examples[0].labels()
    assert hasattr(labels, "action")


def test_to_examples_uses_real_data():
    """Verify the actual training file loads and converts."""
    data = load_training_data("data/training/sql_examples.json")
    examples = to_examples(data)
    assert len(examples) == 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/test_training.py -v`
Expected: FAIL — `src.training` module doesn't exist

- [ ] **Step 3: Create `src/training.py`**

```python
import json

import dspy

from src.schema import InterviewAction


def load_training_data(path: str) -> list[dict]:
    """Load training examples from a JSON file."""
    with open(path) as f:
        return json.load(f)


def to_examples(data: list[dict]) -> list[dspy.Example]:
    """Convert raw training dicts to dspy.Example objects."""
    input_fields = (
        "topic",
        "question",
        "criteria",
        "hint_guidelines",
        "history",
        "user_input",
        "attempt_number",
        "last_evaluation",
        "next_topic",
    )
    examples = []
    for item in data:
        action = InterviewAction(**item["action"])
        example = dspy.Example(
            topic=item["topic"],
            question=item["question"],
            criteria=item["criteria"],
            hint_guidelines=item["hint_guidelines"],
            history=item["history"],
            user_input=item["user_input"],
            attempt_number=item["attempt_number"],
            last_evaluation=item["last_evaluation"],
            next_topic=item["next_topic"],
            action=action,
        ).with_inputs(*input_fields)
        examples.append(example)
    return examples
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/test_training.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/training.py tests/test_training.py
git commit -m "feat: add training data loader for DSPy optimization"
```

---

### Task 10: Create optimization script

**Files:**
- Create: `scripts/optimize.py`

- [ ] **Step 1: Create the optimization script**

Run: `mkdir -p scripts models`

Create `scripts/optimize.py`:

```python
"""DSPy optimization runner.

Compiles InterviewBot using BootstrapFewShot and MIPROv2 optimizers
against hand-crafted SQL training data.

Usage:
    PYTHONPATH=. OPENAI_API_KEY=your-key uv run python scripts/optimize.py
"""

import sys

import dspy

from src.config import init_lm, load_config
from src.modules import InterviewBot
from src.training import load_training_data, to_examples


def evaluation_accuracy(example, prediction, trace=None):
    """Score 1.0 if evaluation matches the gold label."""
    return 1.0 if example.action.evaluation == prediction.action.evaluation else 0.0


def main():
    config = load_config()
    init_lm(config)

    # Load and split training data (80/20)
    data = load_training_data("data/training/sql_examples.json")
    examples = to_examples(data)
    split = int(len(examples) * 0.8)
    trainset = examples[:split]
    valset = examples[split:]

    print(f"Training: {len(trainset)} examples, Validation: {len(valset)} examples")

    # Phase 1: BootstrapFewShot baseline
    print("\n=== Phase 1: BootstrapFewShot ===")
    bootstrap_optimizer = dspy.BootstrapFewShot(
        metric=evaluation_accuracy,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )
    bootstrap_bot = bootstrap_optimizer.compile(
        InterviewBot(),
        trainset=trainset,
    )
    bootstrap_bot.save("models/bootstrap_fewshot.json")
    print("Saved: models/bootstrap_fewshot.json")

    # Phase 2: MIPROv2 optimization
    print("\n=== Phase 2: MIPROv2 ===")
    mipro_optimizer = dspy.MIPROv2(
        metric=evaluation_accuracy,
        auto="medium",
    )
    mipro_bot = mipro_optimizer.compile(
        InterviewBot(),
        trainset=trainset,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )
    mipro_bot.save("models/miprov2.json")
    print("Saved: models/miprov2.json")

    # Evaluate both on validation set
    print("\n=== Evaluation on validation set ===")
    for name, bot in [("Uncompiled", InterviewBot()), ("BootstrapFewShot", bootstrap_bot), ("MIPROv2", mipro_bot)]:
        correct = 0
        for ex in valset:
            pred = bot(**ex.inputs())
            if evaluation_accuracy(ex, pred):
                correct += 1
        acc = correct / len(valset) * 100
        print(f"{name}: {correct}/{len(valset)} = {acc:.0f}%")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script loads without errors**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run python -c "import scripts.optimize; print('OK')" 2>&1 || echo "Expected import error — script is meant to be run directly"`

Note: The script requires a real API key to run. Just verify the syntax is valid:

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run python -c "import ast; ast.parse(open('scripts/optimize.py').read()); print('Syntax OK')"`

- [ ] **Step 3: Add `models/` to `.gitignore`**

Check if `.gitignore` exists and add `models/` directory:

Run: `echo "models/" >> .gitignore`

- [ ] **Step 4: Commit**

```bash
git add scripts/optimize.py .gitignore
git commit -m "feat: add DSPy optimization script (BootstrapFewShot + MIPROv2)"
```

---

### Task 11: Final verification

- [ ] **Step 1: Run full test suite**

Run: `PYTHONPATH=. OPENAI_API_KEY=test uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run linter**

Run: `uv run ruff check src/ tests/ web.py main.py scripts/optimize.py`
Expected: All checks passed

- [ ] **Step 3: Run formatter**

Run: `uv run ruff format --check src/ tests/ web.py main.py scripts/optimize.py`
Expected: All files formatted

- [ ] **Step 4: Final commit if any formatting fixes needed**

```bash
git add -A
git commit -m "style: apply ruff formatting"
```
