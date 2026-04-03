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
- `last_evaluation`: (str) The evaluation result from the most recent turn (e.g., "correct", "incorrect", "ambiguous").
- `evaluation_history`: (list[str]) The sequence of evaluations for the current question.
- `question_summaries`: (list[dict]) A history of metadata for each completed question.

### 2.2 `record_turn(command, evaluation)` Logic
This method replaces the previous `handle_command`.
- Updates `last_evaluation` and appends to `evaluation_history`.
- `NEXT_QUESTION`, `PROMPT_SKIP`: Record the summary (including `evaluation_history`), increment `current_idx`, and reset the per-question counters/history.
- `GIVE_HINT`: Increment `hints_given` and `turns_in_question`.
- `CLARIFY`: Increment `clarifications_requested` and `turns_in_question`.
- All other commands (if any): Increment `turns_in_question`.

## 3. Interaction Logic (`main.py`)

### 3.1 Question Printing
Replace the current check for `orc.attempts == 0` with `orc.turns_in_question == 0`.
- The full question text will only be printed once at the start of the question.

### 3.2 Bot Context
- Pass `orc.last_evaluation` into the `InterviewBot` (requires updating `src/signatures.py`) to provide explicit context on the previous turn's judgment.


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
