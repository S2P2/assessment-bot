# DSPy Interview Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-implement the IT Skill Interview Chatbot using DSPy for evaluation/response and a Python orchestrator for state.

**Architecture:** Unified Predictor (DSPy) + Rigid Orchestrator (Python). The LLM handles the "flexible" dialogue via a single TypedPredictor call, while the Orchestrator enforces "hard" attempt limits.

**Tech Stack:** Python 3.10+, DSPy, Pydantic, Pytest.

---

### Task 1: Project Setup and Data Schema

**Files:**
- Create: `src/data.py`
- Create: `questions.json`
- Test: `tests/test_data.py`

- [ ] **Step 1: Define the `questions.json` structure**
```json
{
  "interview_id": "sql-eval-001",
  "topics": [
    {
      "topic_name": "SQL Basics",
      "questions": [
        {
          "id": "q1",
          "text": "How do you find unique values in a column?",
          "criteria": "Must use the DISTINCT keyword.",
          "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly."
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Create a failing test for data loading**
```python
import pytest
import os
import json
from src.data import load_questions

def test_load_questions_valid():
    test_data = {"interview_id": "test", "topics": [{"topic_name": "T1", "questions": []}]}
    with open("test_questions.json", "w") as f:
        json.dump(test_data, f)
    
    data = load_questions("test_questions.json")
    assert data["interview_id"] == "test"
    os.remove("test_questions.json")
```

- [ ] **Step 3: Implement `load_questions`**
```python
import json

def load_questions(path: str):
    with open(path, "r") as f:
        return json.load(f)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_data.py`

- [ ] **Step 5: Commit**
```bash
git add src/data.py tests/test_data.py questions.json
git commit -m "feat: add data loading and questions schema"
```

---

### Task 2: DSPy Structured Output Schema

**Files:**
- Create: `src/schema.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Write test for Pydantic validation**
```python
from src.schema import InterviewAction
import pytest

def test_interview_action_validation():
    data = {
        "evaluation": "correct",
        "reasoning": "User got it right.",
        "response": "Great job!",
        "command": "NEXT_QUESTION"
    }
    action = InterviewAction(**data)
    assert action.evaluation == "correct"
```

- [ ] **Step 2: Implement `InterviewAction` model**
```python
from pydantic import BaseModel, Field
from typing import Literal

class InterviewAction(BaseModel):
    evaluation: Literal["correct", "incorrect", "ambiguous"] = Field(desc="Evaluation result")
    reasoning: str = Field(desc="Internal logic for the evaluation")
    response: str = Field(desc="The actual message for the candidate")
    command: Literal["NEXT_QUESTION", "GIVE_HINT", "PROMPT_SKIP"] = Field(desc="Instruction to the orchestrator")
```

- [ ] **Step 3: Run test and commit**
Run: `pytest tests/test_schema.py`
```bash
git add src/schema.py tests/test_schema.py
git commit -m "feat: add InterviewAction pydantic schema"
```

---

### Task 3: DSPy Signature and Module

**Files:**
- Create: `src/signatures.py`
- Create: `src/modules.py`
- Test: `tests/test_modules.py`

- [ ] **Step 1: Define the `InterviewTurn` Signature**
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
    action: InterviewAction = dspy.OutputField()
```

- [ ] **Step 2: Implement the `InterviewBot` Module**
```python
import dspy
from src.signatures import InterviewTurn

class InterviewBot(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predictor = dspy.TypedPredictor(InterviewTurn)

    def forward(self, **kwargs):
        return self.predictor(**kwargs)
```

- [ ] **Step 3: Run basic validation and commit**
```bash
git add src/signatures.py src/modules.py
git commit -m "feat: add DSPy signature and module"
```

---

### Task 4: Orchestrator State Management

**Files:**
- Create: `src/orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Write test for state transitions**
```python
from src.orchestrator import InterviewOrchestrator

def test_orchestrator_progression():
    questions = [{"id": "q1", "text": "Q1"}, {"id": "q2", "text": "Q2"}]
    orc = InterviewOrchestrator(questions)
    assert orc.get_current_question()["id"] == "q1"
    orc.handle_command("NEXT_QUESTION")
    assert orc.get_current_question()["id"] == "q2"
    assert orc.attempts == 0
```

- [ ] **Step 2: Implement `InterviewOrchestrator`**
```python
class InterviewOrchestrator:
    def __init__(self, questions, max_attempts=2):
        self.questions = questions
        self.current_idx = 0
        self.attempts = 0
        self.max_attempts = max_attempts
        self.history = []

    def get_current_question(self):
        if self.current_idx >= len(self.questions):
            return None
        return self.questions[self.current_idx]

    def handle_command(self, command):
        if command in ["NEXT_QUESTION", "PROMPT_SKIP"]:
            self.current_idx += 1
            self.attempts = 0
        elif command == "GIVE_HINT":
            self.attempts += 1

    def should_force_skip(self):
        return self.attempts >= self.max_attempts
```

- [ ] **Step 3: Run test and commit**
Run: `pytest tests/test_orchestrator.py`
```bash
git add src/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add InterviewOrchestrator with state logic"
```

---

### Task 5: Main CLI Loop and Integration

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement the main loop**
```python
import dspy
import os
from src.data import load_questions
from src.orchestrator import InterviewOrchestrator
from src.modules import InterviewBot

def main():
    # Setup
    lm = dspy.LM('openai/gpt-4o-mini', api_key=os.getenv("OPENAI_API_KEY"))
    dspy.configure(lm=lm)
    
    data = load_questions("questions.json")
    # Flatten questions for the orchestrator (POC simplification)
    all_questions = []
    for topic in data["topics"]:
        for q in topic["questions"]:
            q["topic_name"] = topic["topic_name"]
            all_questions.append(q)
            
    orc = InterviewOrchestrator(all_questions)
    bot = InterviewBot()
    
    print(f"--- Starting Interview: {data['interview_id']} ---")
    
    while True:
        q = orc.get_current_question()
        if not q:
            break
            
        print(f"\n[{q['topic_name']}] Interviewer: {q['text']}")
        user_input = input("You: ")
        
        # Call DSPy
        result = bot(
            topic=q['topic_name'],
            question=q['text'],
            criteria=q['criteria'],
            hint_guidelines=q['hint_guidelines'],
            history=orc.history[-5:],
            user_input=user_input,
            attempt_number=orc.attempts
        )
        
        action = result.action
        command = action.command
        
        # Orchestrator Override
        if orc.should_force_skip() and command == "GIVE_HINT":
            command = "PROMPT_SKIP"
            print("\n(System: Maximum attempts reached. Suggesting skip.)")
            
        print(f"\nInterviewer: {action.response}")
        
        orc.history.append(f"User: {user_input}")
        orc.history.append(f"Interviewer: {action.response}")
        orc.handle_command(command)

    print("\n--- Interview Complete ---")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit main entry point**
```bash
git add main.py
git commit -m "feat: add main CLI loop and integration"
```
