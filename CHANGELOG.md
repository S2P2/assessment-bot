# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **DSPy Reasoning Strategy**: Switched from `dspy.Predict` to `dspy.ChainOfThought` for more robust evaluation logic.
- **Signature Refinement**: Simplified `InterviewTurn` signature and moved detailed instructions to field descriptions per DSPy best practices.
- **UI Flow**: Modified the CLI loop to only print the full question on the first attempt, creating a cleaner chat experience during hint sequences.

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

### Changed
- Refactored `src/modules.py` to use `dspy.Predict` for compatibility with the latest DSPy 3.x release.
