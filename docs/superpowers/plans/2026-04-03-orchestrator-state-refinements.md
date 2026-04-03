# Orchestrator State & Interaction Refinements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix double-printing of questions and improve state tracking for turns, hints, and clarifications.

**Architecture:** Update `InterviewOrchestrator` to track granular interaction state and provide `last_evaluation` as a session variable to the LLM.

**Tech Stack:** Python 3.13, DSPy, pytest.

---

### Task 1: Update Orchestrator State and `record_turn` Method

**Files:**
- Modify: `src/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Update `InterviewOrchestrator.__init__`**
Add the new state variables for tracking turns, hints, clarifications, and summaries.

```python
    def __init__(self, questions, max_attempts=2):
        self.questions = questions
        self.current_idx = 0
        self.attempts = 0 # Backward compatibility
        self.max_attempts = max_attempts
        self.history = []
        
        # New State
        self.turns_in_question = 0
        self.hints_given = 0
        self.clarifications_requested = 0
        self.last_evaluation = "None"
        self.evaluation_history = []
        self.question_summaries = []
```

- [ ] **Step 2: Update `tests/test_orchestrator.py` with failing tests for `record_turn`**
Replace `handle_command` calls with `record_turn` and add assertions for the new counters.

```python
def test_orchestrator_record_turn():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    
    # First turn: Clarify
    orc.record_turn("CLARIFY", "ambiguous")
    assert orc.turns_in_question == 1
    assert orc.clarifications_requested == 1
    assert orc.last_evaluation == "ambiguous"
    
    # Second turn: Hint
    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.turns_in_question == 2
    assert orc.hints_given == 1
    assert orc.attempts == 1 # Backward compatibility
    
    # Third turn: Next Question
    orc.record_turn("NEXT_QUESTION", "correct")
    assert len(orc.question_summaries) == 1
    assert orc.question_summaries[0]["final_evaluation"] == "correct"
    assert orc.turns_in_question == 0 # Reset
```

- [ ] **Step 3: Implement `record_turn` in `src/orchestrator.py`**
Implement the logic to update counters and record summaries.

```python
    def record_turn(self, command, evaluation):
        self.last_evaluation = evaluation
        self.evaluation_history.append(evaluation)
        self.turns_in_question += 1

        if command in ["NEXT_QUESTION", "PROMPT_SKIP"]:
            # Record summary before moving on
            q = self.get_current_question()
            summary = {
                "question_id": q.get("id"),
                "final_evaluation": evaluation,
                "total_turns": self.turns_in_question,
                "hints_used": self.hints_given,
                "clarifications_used": self.clarifications_requested,
                "was_force_skipped": command == "PROMPT_SKIP"
            }
            self.question_summaries.append(summary)
            
            self.current_idx += 1
            self.turns_in_question = 0
            self.hints_given = 0
            self.clarifications_requested = 0
            self.attempts = 0
            self.evaluation_history = []
        elif command == "GIVE_HINT":
            self.hints_given += 1
            self.attempts += 1 # maintain for should_force_skip
        elif command == "CLARIFY":
            self.clarifications_requested += 1
```

- [ ] **Step 4: Run tests and verify they pass**
Run: `uv run pytest tests/test_orchestrator.py`

- [ ] **Step 5: Commit**
```bash
git add src/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: replace handle_command with record_turn and add detailed state tracking"
```

---

### Task 2: Update `InterviewTurn` Signature

**Files:**
- Modify: `src/signatures.py`

- [ ] **Step 1: Add `last_evaluation` to `InterviewTurn`**

```python
class InterviewTurn(dspy.Signature):
    """Evaluate candidate answer and generate the next interviewer response."""
    topic = dspy.InputField()
    question = dspy.InputField()
    criteria = dspy.InputField()
    hint_guidelines = dspy.InputField()
    history = dspy.InputField(desc="Previous turns as a list of strings")
    user_input = dspy.InputField()
    attempt_number = dspy.InputField()
    last_evaluation = dspy.InputField(desc="The evaluation result from the previous turn, or 'None' if first turn.")
    next_topic = dspy.InputField(desc="Name of the next topic, or None if finishing.")
    action: InterviewAction = dspy.OutputField(desc="Structured response including evaluation, reasoning, and the next response string. If command is NEXT_QUESTION, the response MUST be a concluding statement or transition. It MUST NOT ask follow-up questions. Use 'CLARIFY' if the user is too vague to evaluate.")
```

- [ ] **Step 2: Commit**
```bash
git add src/signatures.py
git commit -m "feat: add last_evaluation to InterviewTurn signature"
```

---

### Task 3: Update `main.py` Interaction Logic

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Pass `last_evaluation` to `bot()` call**

```python
        result = bot(
            topic=q["topic_name"],
            question=q["text"],
            criteria=q["criteria"],
            hint_guidelines=q["hint_guidelines"],
            history=orc.history[-5:],
            user_input=user_input,
            attempt_number=orc.attempts,
            last_evaluation=orc.last_evaluation, # NEW
            next_topic=orc.get_next_topic_name()
        )
```

- [ ] **Step 2: Update question printing logic**

```python
        # Only print the full question if this is the first turn
        if orc.turns_in_question == 0:
            print(f"\n[{q['topic_name']}] Interviewer: {q['text']}")
```

- [ ] **Step 3: Update state using `record_turn`**

```python
        print(f"\nInterviewer: {action.response}")

        orc.history.append(f"User: {user_input}")
        orc.history.append(f"Interviewer: {action.response}")
        orc.record_turn(command, action.evaluation) # REPLACES handle_command
```

- [ ] **Step 4: Commit**
```bash
git add main.py
git commit -m "feat: update main loop to use turns_in_question and record_turn"
```

---

### Task 4: Manual Verification

- [ ] **Step 1: Run the bot and test `CLARIFY`**
Run: `uv run python main.py`
- Answer "it depends" to trigger `CLARIFY`.
- **Expected:** Bot asks for clarification. Root question is **NOT** reprinted.

- [ ] **Step 2: Run tests one last time**
Run: `uv run pytest tests/test_orchestrator.py`
