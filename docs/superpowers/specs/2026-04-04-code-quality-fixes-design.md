# Design Spec: Code Quality Fixes (v0.3.2)

**Date:** 2026-04-04
**Status:** Approved
**Topic:** Error handling, misleading comments, placeholder text, graceful shutdown, and test coverage gaps.

## 1. Goal

Address quality issues found during project review: missing error handling that produces unhelpful crash messages, a misleading comment, a template placeholder, no graceful Ctrl+C handling, data transformation in the wrong layer, test coverage gaps, and a trivial wrapper module.

## 2. Changes

### 2.1 Exit on missing API key (`main.py`)

Replace the warning-only check with `sys.exit()` so the user gets a clear, actionable message instead of a cryptic auth failure later.

### 2.2 Error handling around LLM calls (`main.py`)

Wrap the `bot()` call in the interview loop with try/except:
- Retry up to 2 times on transient failures (connection errors, rate limits)
- On persistent failure, print a friendly message and let the user re-enter their answer instead of crashing

### 2.3 Error handling in data loader (`src/data.py`)

Wrap `open()` and `json.load()` with specific exception handling:
- `FileNotFoundError` → clear message with the path
- `json.JSONDecodeError` → clear message with the path and error detail

### 2.4 Fix misleading comment (`src/orchestrator.py`)

Change `# Backward compatibility` on `self.attempts` to `# Hint attempts (drives force-skip logic)` to accurately describe its purpose.

### 2.5 Replace placeholder description (`pyproject.toml`)

Change `description = "Add your description here"` to `description = "Terminal-based IT skill interview bot powered by DSPy"`.

### 2.6 Graceful Ctrl+C handling (`main.py`)

Wrap the interview loop in a try/except for `KeyboardInterrupt`, printing a clean exit message instead of a raw traceback.

### 2.7 Move question flattening to data layer (`src/data.py`)

Extract the question flattening loop from `main.py` into `flatten_questions()` in `src/data.py`. Fix the mutation bug by creating new dicts with `{**q, "topic_name": topic["topic_name"]}` instead of modifying originals in-place.

### 2.8 MLflow span naming (`main.py`)

Update span name from `f"Turn: {q['topic_name']}"` to `f"{q['topic_name']}: {q['id']}"`.

## 3. Test Coverage

### 3.1 Error path tests (`tests/test_data.py`)

- `load_questions` with nonexistent file exits with clear message
- `load_questions` with invalid JSON exits with clear message

### 3.2 Orchestrator edge cases (`tests/test_orchestrator.py`)

- `record_turn` with invalid/unexpected command
- `should_force_skip` at exactly max attempts and one over
- `get_next_topic_name` when on last question (returns `None`)
- `get_current_question` with empty questions list (returns `None`)

### 3.3 Schema validation (`tests/test_schema.py`)

- Valid action with each evaluation type: correct, incorrect, ambiguous
- Valid action with each command: NEXT_QUESTION, GIVE_HINT, PROMPT_SKIP, CLARIFY
- Invalid evaluation value raises ValidationError
- Invalid command value raises ValidationError

## 4. Out of Scope

- **Removing `src/modules.py`**: The wrapper is trivial but DSPy convention is to subclass `dspy.Module`. Keeping it allows adding few-shot examples or multi-step reasoning later without changing call sites. YAGNI says remove it, but the cost of keeping it is near-zero and it follows DSPy patterns.
