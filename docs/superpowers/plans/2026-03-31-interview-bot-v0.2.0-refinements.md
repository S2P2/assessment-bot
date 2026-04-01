# Interview Bot Refinements (v0.2.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve interview transitions, topic awareness, and evaluation strictness.

**Architecture:** Extend the Python Orchestrator with topic lookahead and refine the DSPy Signature/Module constraints.

**Tech Stack:** Python 3.13, DSPy, Pydantic, Pytest, uv.

---

### Task 1: Update Orchestrator Topic Awareness

**Files:**
- Modify: `src/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test for `get_next_topic_name`**
```python
def test_orchestrator_next_topic_name():
    questions = [
        {"id": "q1", "topic_name": "SQL"},
        {"id": "q2", "topic_name": "SQL"},
        {"id": "q3", "topic_name": "Python"}
    ]
    orc = InterviewOrchestrator(questions)
    # Current is q1, next is q2 (same topic)
    assert orc.get_next_topic_name() == "SQL"
    
    orc.handle_command("NEXT_QUESTION")
    # Current is q2, next is q3 (new topic)
    assert orc.get_next_topic_name() == "Python"
    
    orc.handle_command("NEXT_QUESTION")
    # Current is q3, no next question
    assert orc.get_next_topic_name() is None
```

- [ ] **Step 2: Run test to verify it fails**
Run: `$env:PYTHONPATH="."; uv run pytest tests/test_orchestrator.py`
Expected: `AttributeError: 'InterviewOrchestrator' object has no attribute 'get_next_topic_name'`

- [ ] **Step 3: Implement `get_next_topic_name`**
```python
class InterviewOrchestrator:
    # ... existing methods ...
    def get_next_topic_name(self):
        next_idx = self.current_idx + 1
        if next_idx >= len(self.questions):
            return None
        return self.questions[next_idx]["topic_name"]
```

- [ ] **Step 4: Run test to verify it passes**
Run: `$env:PYTHONPATH="."; uv run pytest tests/test_orchestrator.py`

- [ ] **Step 5: Commit**
```bash
git add src/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add get_next_topic_name to InterviewOrchestrator"
```

---

### Task 2: Refine Signature and Field Constraints

**Files:**
- Modify: `src/signatures.py`

- [ ] **Step 1: Update `InterviewTurn` signature**
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
    next_topic = dspy.InputField(desc="Name of the next topic, or None if finishing.")
    action: InterviewAction = dspy.OutputField(desc="Structured response including evaluation, reasoning, and the next response string. If command is NEXT_QUESTION, the response MUST be a concluding statement or transition. It MUST NOT ask follow-up questions or prompt for further input, as the system will immediately move to the next item.")
```

- [ ] **Step 2: Commit**
```bash
git add src/signatures.py
git commit -m "refactor: update signature with next_topic and hard constraints"
```

---

### Task 3: Integration and Environment Setup

**Files:**
- Modify: `main.py`
- Modify: `questions.json`

- [ ] **Step 1: Update `main.py` to pass `next_topic`**
```python
        # ... inside while loop ...
        # Call DSPy
        result = bot(
            topic=q["topic_name"],
            question=q["text"],
            criteria=q["criteria"],
            hint_guidelines=q["hint_guidelines"],
            history=orc.history[-5:],
            user_input=user_input,
            attempt_number=orc.attempts,
            next_topic=orc.get_next_topic_name()
        )
```

- [ ] **Step 2: Refine `questions.json` criteria**
Update the "Python Basics" question criteria:
```json
{
  "id": "q3",
  "text": "How do you handle exceptions in Python to prevent the program from crashing?",
  "criteria": "Must explicitly mention 'try' and 'except' blocks. Note: 'catch' is incorrect syntax in Python.",
  "hint_guidelines": "Ask about the block-based structure used to catch errors during execution."
}
```

- [ ] **Step 3: Run all tests to ensure stability**
Run: `$env:PYTHONPATH="."; uv run pytest`

- [ ] **Step 4: Commit**
```bash
git add main.py questions.json
git commit -m "feat: integrate next_topic and refine question criteria"
```

---

### Task 4: Manual Verification

- [ ] **Step 1: Run the application and simulate the "SQL Basics" to "Python Basics" transition**
Run: `uv run python main.py`
Verify:
1. When answering the second SQL question correctly, the bot mentions "Python Basics" (the `next_topic`) but DOES NOT ask a question like "Are you ready?".
2. When answering "try catch" to the Python question, the bot gives a hint or corrects you without finishing (if criteria specifies strictness).
