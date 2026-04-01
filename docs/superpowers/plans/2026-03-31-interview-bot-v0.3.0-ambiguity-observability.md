# Interview Bot v0.3.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the CLARIFY command and MLflow autologging.

**Architecture:** Extend schema, orchestrator, and main entry point.

**Tech Stack:** Python 3.13, DSPy, Pydantic, MLflow, uv.

---

### Task 1: Update Schema and Orchestrator

**Files:**
- Modify: `src/schema.py`
- Modify: `src/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Update `InterviewAction` command Literal**
```python
class InterviewAction(BaseModel):
    # ...
    command: Literal["NEXT_QUESTION", "GIVE_HINT", "PROMPT_SKIP", "CLARIFY"] = Field(
        description="Instruction to the orchestrator. Use 'CLARIFY' if the user is too vague to evaluate."
    )
```

- [ ] **Step 2: Write failing test for `CLARIFY` command**
```python
def test_orchestrator_clarify():
    questions = [{"id": "q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.handle_command("CLARIFY")
    assert orc.attempts == 0  # Should NOT increment
    assert orc.current_idx == 0 # Should NOT move on
```

- [ ] **Step 3: Update `handle_command`**
```python
    def handle_command(self, command):
        if command in ["NEXT_QUESTION", "PROMPT_SKIP"]:
            self.current_idx += 1
            self.attempts = 0
        elif command == "GIVE_HINT":
            self.attempts += 1
        # CLARIFY does nothing to state (keeps same question, same attempts)
```

- [ ] **Step 4: Run tests to verify**
Run: `$env:PYTHONPATH="."; uv run pytest tests/test_orchestrator.py`

- [ ] **Step 5: Commit**
```bash
git add src/schema.py src/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add CLARIFY command to schema and orchestrator"
```

---

### Task 2: Refine Signature and Enable MLflow

**Files:**
- Modify: `src/signatures.py`
- Modify: `main.py`
- Modify: `pyproject.toml` (via `uv add`)

- [ ] **Step 1: Update `InterviewTurn` field description**
Include `CLARIFY` in the `action` OutputField description in `src/signatures.py`.

- [ ] **Step 2: Add `mlflow` dependency**
Run: `uv add mlflow`

- [ ] **Step 3: Initialize MLflow autologging in `main.py`**
```python
import mlflow
# ...
def main():
    mlflow.set_experiment("Interview_Bot_v0.3.0")
    mlflow.dspy.autolog()
    # ...
```

- [ ] **Step 4: Commit**
```bash
git add src/signatures.py main.py pyproject.toml uv.lock
git commit -m "feat: add MLflow autologging and update signature"
```

---

### Task 3: Manual Verification

- [ ] **Step 1: Verify `CLARIFY` flow**
Run: `uv run python main.py`
Try answering with "write good code" and see if the bot asks for more detail without counting it as an attempt.

- [ ] **Step 2: Verify MLflow Tracing**
Check the `mlruns` directory or run `mlflow ui` to verify that each interview turn is logged with a trace.
