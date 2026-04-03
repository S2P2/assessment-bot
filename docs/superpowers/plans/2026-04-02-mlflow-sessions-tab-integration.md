# Implementation Plan: MLflow "Sessions" Tab Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate the MLflow "Sessions" tab by wrapping DSPy calls in a traced function that injects `mlflow.trace.session` metadata.

**Architecture:** Create `src/tracing.py` to house a wrapper function using `mlflow.start_span` and `mlflow.update_current_trace`. Update `main.py` to use this wrapper.

**Tech Stack:** `mlflow`, `dspy`

---

### Task 1: Create the Tracing Wrapper

**Files:**
- Create: `src/tracing.py`

- [ ] **Step 1: Create `src/tracing.py` with `traced_bot_call`**

```python
import mlflow

def traced_bot_call(bot, session_id, **kwargs):
    """
    Wraps the bot call to inject MLflow Session metadata.
    This ensures the trace appears in the 'Sessions' tab under Observability.
    """
    # Use start_span to create a parent for all internal DSPy traces in this turn
    with mlflow.start_span(name=f"Turn: {kwargs.get('topic', 'Interaction')}") as span:
        # Pass inputs to the span for visibility in UI
        span.set_inputs(kwargs)
        
        # This is the CRITICAL part for the 'Sessions' tab
        mlflow.update_current_trace(
            metadata={
                "mlflow.trace.session": str(session_id),
                "mlflow.trace.user": kwargs.get("user_id", "unknown")
            }
        )
        
        # Call the actual DSPy bot module
        result = bot(**kwargs)
        
        # Set outputs for the span
        span.set_outputs({"action": result.action.to_dict() if hasattr(result.action, 'to_dict') else str(result.action)})
        
        return result
```

- [ ] **Step 2: Commit**

```bash
git add src/tracing.py
git commit -m "feat: add tracing wrapper for MLflow session grouping"
```

### Task 2: Integrate Wrapper into `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update imports and bot call in `main.py`**

```python
# Add import
from src.tracing import traced_bot_call

# ... inside the loop ...
                with mlflow.start_run(run_name=f"Turn {orc.turn_number}: {q['topic_name']}", nested=True):
                    # ... tags and params ...
                    
                    # Replace direct bot call with traced_bot_call
                    result = traced_bot_call(
                        bot=bot,
                        session_id=orc.session_id,
                        user_id=username,
                        topic=q["topic_name"],
                        question=q["text"],
                        criteria=q["criteria"],
                        hint_guidelines=q["hint_guidelines"],
                        history=orc.history[-5:],
                        user_input=user_input,
                        attempt_number=orc.attempts,
                        next_topic=orc.get_next_topic_name()
                    )
# ... rest of logic ...
```

- [ ] **Step 2: Run verification**

Run `python main.py`, interact with it, and check MLflow UI.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: use traced_bot_call in main.py for session grouping"
```

### Task 3: Final Verification

- [ ] **Step 1: Verify in MLflow UI**

1. Go to **Observability -> Sessions**.
2. Confirm your session appears there.
3. Drill down to see the turns inside.
4. Go to **Evaluation runs** and confirm the parent-child hierarchy is still correct.

- [ ] **Step 2: Commit and Cleanup**

```bash
git status
```
