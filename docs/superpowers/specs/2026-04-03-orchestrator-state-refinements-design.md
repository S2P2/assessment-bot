# Design Spec: Orchestrator State & Interaction Refinements (v0.3.1)

**Date:** 2026-04-03
**Status:** Approved
**Topic:** State tracking for turns, hints, and clarifications to improve UX and metadata collection.

## 1. Goal
Fix the issue where the interviewer re-prints the full question text after a `CLARIFY` command, and improve state tracking to capture metadata for future performance analysis.

## 2. Architecture & State Changes

### 2.1 `InterviewOrchestrator` State
The orchestrator will track the following per-question state:
- `turns_in_question`: (int) Increments on **every** interaction for the current question. Resets on `NEXT_QUESTION`.
- `hints_given`: (int) Increments only on `GIVE_HINT`. Resets on `NEXT_QUESTION`.
- `clarifications_requested`: (int) Increments only on `CLARIFY`. Resets on `NEXT_QUESTION`.
- `question_summaries`: (list[dict]) A history of metadata for each completed question.

**Example Summary Structure:**
```python
{
    "question_id": "q1",
    "final_evaluation": "correct",
    "total_turns": 3,
    "hints_used": 1,
    "clarifications_used": 1,
    "was_force_skipped": False
}
```

### 2.2 `handle_command` Logic
- `handle_command(command, evaluation=None)`: Updated to accept the optional evaluation result.
- `NEXT_QUESTION`, `PROMPT_SKIP`: Record the summary (including `evaluation`), increment `current_idx`, and reset the per-question counters.
- `GIVE_HINT`: Increment `hints_given` and `turns_in_question`.
- `CLARIFY`: Increment `clarifications_requested` and `turns_in_question`.
- All other commands (if any): Increment `turns_in_question`.

## 3. Interaction Logic (`main.py`)

### 3.1 Question Printing
Replace the current check for `orc.attempts == 0` with `orc.turns_in_question == 0`.
- The full question text (e.g., "How do you find unique values in a column?") will only be printed once at the start of the question.
- Subsequent `CLARIFY` or `GIVE_HINT` responses from the bot will provide the follow-up message without re-printing the root question.

## 4. Testing Strategy

### 4.1 Unit Tests (`tests/test_orchestrator.py`)
- Verify `turns_in_question` increments on all commands.
- Verify `clarifications_requested` only increments on `CLARIFY`.
- Verify `hints_given` only increments on `GIVE_HINT`.
- Verify `turns_in_question == 0` is true only at the start of a question.
- Verify metadata summaries are correctly recorded upon moving to the next question.

### 4.2 Manual Verification
- Run the bot and trigger a `CLARIFY` action (e.g., answer with "it depends").
- Confirm the bot asks for clarification but DOES NOT re-print the original question text.
