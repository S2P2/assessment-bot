# Design Spec: Interview Bot v0.3.0 (Ambiguity & Observability)

## 1. Overview
This update introduces two key features:
- **Ambiguity Handling**: A new `CLARIFY` command that allows the LLM to ask for more specific information when a user's answer is too vague (e.g., "write good code"), without incrementing the attempt/hint counter.
- **MLflow Observability**: Native integration with MLflow for automatic tracing of DSPy calls, including reasoning, inputs, and outputs.

## 2. Goals & Success Criteria
- **Fair Transitions**: Users shouldn't be penalized (given a hint or skipped) for providing vague but technically correct or "it depends" style answers.
- **Traceability**: Every interview turn should be automatically logged to MLflow with a full trace of the LLM's reasoning and inputs.

## 3. Architecture Changes

### 3.1 Schema (`src/schema.py`)
- Update `InterviewAction`'s `command` literal to include `"CLARIFY"`.
- Update field description to guide the LLM on when to use `CLARIFY`.

### 3.2 Orchestrator (`src/orchestrator.py`)
- Update `handle_command(command)`:
  - If `command == "CLARIFY"`, the `attempts` counter MUST NOT be incremented.
  - The `current_idx` MUST NOT be incremented.

### 3.3 DSPy Signature (`src/signatures.py`)
- Update the `action: InterviewAction` output field description to explicitly mention the `CLARIFY` command.

### 3.4 Entry Point (`main.py`)
- Import `mlflow`.
- Add `mlflow.dspy.autolog()` at the beginning of `main()`.
- Set `mlflow.set_experiment("Interview_Bot_v0.3.0")`.

## 4. Testing Strategy
- **Unit Test**: Update `tests/test_orchestrator.py` to verify `CLARIFY` behavior (non-incrementing `attempts`).
- **Integration Test**: Verify MLflow traces are generated after running `main.py` and answering a question.

## 5. Potential Improvements (Post-v0.3.0)
- **Trace Analysis**: Use MLflow's evaluation tools to compare different DSPy models or prompts.
- **Dynamic Strictness**: Have the LLM decide when to be more or less lenient based on the candidate's previous performance (visible in `history`).
