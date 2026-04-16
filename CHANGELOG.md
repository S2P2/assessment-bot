# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-04-16

### Added
- **Web UI CLI Arguments**: `web.py` now accepts `--questions`, `--model`, `--base-url`, and `--no-mlflow` flags, matching `main.py`. Uses `parse_known_args()` to avoid conflicts with pytest's CLI args when web.py is imported during tests.

### Fixed
- **UTF-8 encoding on Windows**: `load_questions()` now explicitly opens JSON files with `encoding="utf-8"` instead of relying on the OS default (cp874 on Thai Windows), preventing `UnicodeDecodeError` with non-ASCII question files.

### Dependencies
- Bumped cryptography 46.0.6 → 46.0.7 (CVE-2026-39892).
- Bumped pytest 9.0.2 → 9.0.3 (CVE-2025-71176).
- Bumped pillow 12.1.1 → 12.2.0.
- Bumped python-multipart 0.0.24 → 0.0.26.

## [0.4.1] - 2026-04-10

### Fixed
- **Session file proliferation**: Files now named by user_id instead of UUID — one file per user, no more scanning.
- **Empty "..." bubble on interview start**: Suppress Gradio pending indicator with `show_progress="hidden"` on start event.
- **User answer delayed until LLM responds**: User message appears immediately via split callbacks.
- **No Send button**: Added Send button next to the chat textbox.
- **Textbox not disabled when interview completes**: Textbox becomes read-only after interview ends.
- **Sidebar history items on same line**: History now renders as markdown list with one item per line.

### Security
- **Path traversal guard**: Session file naming validates user_id to prevent directory traversal attacks.

## [0.4.0] - 2026-04-09

### Added
- **Gradio 6 Web UI**: Candidate-facing interview interface at `web.py` with sidebar progress panel and chat area.
- **Session Persistence**: JSON file-based session storage (`sessions/`) with server-side registry. Candidates can resume interrupted interviews by re-entering their user ID.
- **Server-Side Security**: Question criteria, hint guidelines, and evaluation details are kept in a server-side registry and never sent to the browser via `gr.State()`.
- **Shared Config Module**: Extracted `src/config.py` from `main.py` with `load_config()`, `init_lm()`, and `load_interview_data()` — shared by CLI and web app.
- **Integration Tests**: 21 new tests covering config, session persistence, web UI helpers, security, and full interview lifecycle.
- **CLI Arguments**: `main.py` now accepts `--questions`, `--model`, `--base-url`, and `--no-mlflow` flags to override `.env` defaults without editing files.
- **Thai Question Set**: Added `questions_th.json` — a Thai translation of the default question set for testing.

### Changed
- **main.py**: Refactored to use shared `src/config.py` module. No behavior change.
- **Version**: Bumped from 0.3.3 to 0.4.0.

### Dependencies
- Added `gradio>=6.0`.

## [0.3.3] - 2026-04-05

### Added
- **JSON Schema Validation**: `questions.json` is now validated against `schemas/questions.schema.json` (Draft 2020-12) at load time. Structural errors (missing fields, extra properties) are caught with clear messages.
- **Topic IDs**: Each topic now has a `topic_id` field (lowercase, alphanumeric + dashes) used to derive question IDs.
- **Computed Question IDs**: Question IDs are no longer manually assigned. They are computed from `topic_id` + running number (e.g., `sql-1`, `sql-2`, `python-1`).
- **Project Configuration**: Added `CLAUDE.md` with project structure and `uv run` instructions. Added `MODEL` to `.env.example`.

### Changed
- **jsonschema**: Promoted from transitive to direct dependency in `pyproject.toml`.

### Removed
- **Manual Question IDs**: Removed `id` field from question objects in `questions.json`.

## [0.3.2] - 2026-04-04

### Added
- **Model Configuration**: Added `MODEL` environment variable to allow customizable model selection via `.env` (defaults to `openai/qwen3.5:4b`).
- **Question Flattening**: Moved question flattening logic from `main.py` to `flatten_questions()` in `src/data.py`. No longer mutates question dicts in-place.
- **LLM Retry Logic**: Bot calls now retry up to 2 times on transient failures before surfacing an error.
- **Graceful Exit**: Ctrl+C during interview prints a clean exit message instead of a traceback.
- **Test Coverage**: Added tests for error paths (missing files, invalid JSON), orchestrator edge cases (empty questions, unknown commands, boundary conditions), and schema validation (all evaluation/command types, invalid values).

### Changed
- **MLflow Experiment**: Renamed from versioned `Interview_Bot_v0.3.1` to stable `Interview_Bot`. Version is now tracked as trace metadata for cross-version filtering.
- **Span Naming**: MLflow span names changed from `Turn: {topic}` to `{topic}: {question_id}` for better trace filtering.
- **Error Handling**: `load_questions()` now exits with clear messages for missing files and invalid JSON instead of raw tracebacks.
- **API Key Check**: Missing `OPENAI_API_KEY` now exits immediately instead of printing a warning and crashing later.
- **Orchestrator Comment**: Fixed misleading `# Backward compatibility` comment on `attempts` field.
- **Project Description**: Replaced template placeholder in `pyproject.toml` with actual description.

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
