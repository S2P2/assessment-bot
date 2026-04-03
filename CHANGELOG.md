# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-04-03

### Added
- **Detailed Interaction Tracking**: `InterviewOrchestrator` now tracks `turns_in_question`, `hints_given`, `clarifications_requested`, and `question_summaries` for more granular session analytics.
- **Evaluation History**: Added `last_evaluation` and `evaluation_history` to the orchestrator to provide context for the next turn.

### Changed
- **Orchestrator API**: Replaced `handle_command` with a more descriptive `record_turn` method that updates all state counters and records question summaries.
- **Signature Refinement**: Updated `InterviewTurn` signature to include `last_evaluation` as an input field, allowing the LLM to adjust its response based on the previous evaluation (e.g., if the user was just asked to clarify).
- **UI Logic**: Switched the UI's question-printing logic to use `turns_in_question` instead of `attempts`, ensuring the question is only printed once even if multiple clarifications occur.

## [0.3.0] - 2026-04-01

### Added
- **Ambiguity Handling**: Introduced the `CLARIFY` command to handle vague answers without penalizing the candidate's attempt counter.
- **MLflow Observability**: Enabled native `mlflow.dspy.autolog()` for automatic tracing of DSPy calls, reasoning, and metadata.

### Changed
- **State Logic**: Updated `InterviewOrchestrator` to support the `CLARIFY` command by maintaining the current state (no counter increment).

## [0.2.0] - 2026-03-31

### Changed
- **DSPy Reasoning Strategy**: Switched from `dspy.Predict` to `dspy.ChainOfThought` for more robust evaluation logic.
- **Signature Refinement**: Simplified `InterviewTurn` signature and moved detailed instructions to field descriptions per DSPy best practices.
- **UI Flow**: Modified the CLI loop to only print the full question on the first attempt, creating a cleaner chat experience during hint sequences.
- **Topic Awareness**: Orchestrator now tracks and identifies the `next_topic` to improve transition context.

## [0.1.0] - 2026-03-31

### Added
- **Initial POC Release**: A functional terminal-based IT skill interview bot.
- **DSPy Module Integration**: Implemented `InterviewBot` using structured `dspy.Predict` and signatures.
- **Python Orchestrator**: Managed state machine for question progression, history tracking, and hint/skip logic.
- **Pydantic Schemas**: Structured output validation for the LLM's actions and commands.
- **Configuration Support**: Support for `OPENAI_API_KEY`, `OPENAI_BASE_URL` via environment or `.env` file.
- **Automated Testing**: Comprehensive Pytest suite for core data, schema, and orchestration logic.
- **Project Tooling**: Initial project setup using `uv` with reproducible dependencies.
- **Project Documentation**: Initial README and Changelog.
