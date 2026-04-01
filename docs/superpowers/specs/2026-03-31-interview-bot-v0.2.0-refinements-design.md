# Design Spec: Interview Bot Refinements (v0.2.0)

## 1. Overview
This update addresses three key behavioral issues:
- **Ghost Follow-ups**: The LLM asking a question while the system moves to the next item.
- **Syntax Leniency**: The LLM accepting incorrect syntax (e.g., "try/catch" in Python).
- **Topic Awareness**: The LLM not knowing what topic is coming next.

## 2. Goals & Success Criteria
- **Rigid Transitions**: Ensure `NEXT_QUESTION` responses never prompt the user.
- **Contextual Awareness**: Provide the name of the next topic to the LLM.
- **Strict Evaluation**: Enable per-question syntax strictness via JSON criteria.

## 3. Architecture Changes

### 3.1 Orchestrator (`src/orchestrator.py`)
- Add `get_next_topic_name()`:
  - Checks `current_idx + 1`.
  - Returns the `topic_name` of the next question if it exists, otherwise `None`.
- Update `main.py` to pass `next_topic` to the `InterviewBot` call.

### 3.2 DSPy Signature (`src/signatures.py`)
- Add `next_topic` as an `InputField`.
- Update `action: InterviewAction` output field description:
  - **Constraint**: If `command` is `NEXT_QUESTION`, the `response` MUST be a concluding statement or transition. It MUST NOT ask follow-up questions or prompt for further input.

### 3.3 Data Schema (`questions.json`)
- Refine `criteria` for technical questions to require specific syntax (e.g., "Must use 'try' and 'except' blocks; 'catch' is incorrect in Python").

## 4. Testing Strategy
- **Unit Test**: Verify `get_next_topic_name()` in `tests/test_orchestrator.py`.
- **Manual Verification**: Run `main.py` and confirm the transition from SQL to Python handles the topic name correctly and doesn't ask "ghost" questions.

## 5. Potential Improvements (Post-v0.2.0)
- **Score Summary**: Have the LLM provide a summary of performance when `next_topic` is `None`.
- **Ambiguity Detection**: Explicitly handle "write good code" style answers with a `CLARIFY` command.
