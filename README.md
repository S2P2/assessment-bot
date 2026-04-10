# DSPy Interview Bot POC (v0.4.1)

An IT skill interview chatbot with both **terminal** and **web UI** interfaces, built with the **DSPy framework**. It uses a Unified Predictor model with **Chain of Thought** reasoning to evaluate answers and generate responses in a single LLM call, while a Python Orchestrator manages the rigid conversation state.

## New in v0.4.1

- **Session file naming**: Files named by user_id instead of UUID — one file per user, no more proliferation on restart.
- **Chained callbacks**: User messages appear instantly (no waiting for LLM response).
- **Send button**: Added alongside the chat textbox.
- **Textbox auto-disable**: Input locks when the interview completes.
- **Sidebar history**: Each evaluation item renders on its own line.
- **Path traversal guard**: Session file naming validates user_id to prevent directory traversal.

## New in v0.4.0

- **Gradio 6 Web UI**: Candidate-facing interview interface with sidebar progress panel and chat area.
- **Session Persistence**: JSON file-based session storage with server-side registry. Candidates can resume interrupted interviews by re-entering their user ID.
- **Server-Side Security**: Question criteria, hint guidelines, and evaluation details are kept server-side and never sent to the browser.

## Features

- **Unified Logic**: Evaluation and response generation handled in a single structured call using `dspy.ChainOfThought`.
- **Structured Output**: Uses Pydantic models in `src/schema.py` to ensure consistent evaluation and command logic.
- **Orchestration**: Manages question progression, attempt limits (max 2 hints), and conversation history in `src/orchestrator.py`.
- **Customizable**: Full support for custom OpenAI `base_url`, configurable model, and `.env` files.
- **MLflow Tracing**: Every turn is traced with user/session metadata and named spans (`{topic}: {question_id}`) for easy filtering.
- **Resilient**: Retries on transient LLM failures, exits cleanly on Ctrl+C, and gives clear error messages for missing config or data files.
- **Modern Tooling**: Managed with `uv` for fast, reproducible Python environments.
- **Web UI**: Gradio 6 interface with sidebar progress, chat area, session persistence, and resumable interviews.

## Setup

1. **Install uv**:
   Follow instructions at [astral.sh/uv](https://astral.sh/uv).

2. **Clone and Install**:
   ```bash
   uv sync
   ```

3. **Configure Environment**:
   Create a `.env` file or set environment variables:
   ```bash
   OPENAI_API_KEY=your-key-here
   OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
   MODEL=openai/qwen3.5:4b                    # Optional (defaults to openai/qwen3.5:4b)
   ```

## Usage

### Run the Web UI
```bash
uv run python web.py
```
Then navigate to `http://localhost:7860` in your browser.

### Run the CLI Interview
```bash
# Default (questions.json, model from .env)
uv run python main.py

# Thai questions with a different model
uv run python main.py --questions questions_th.json --model openai/gpt-4o

# Quick test without MLflow
uv run python main.py --questions questions_th.json --no-mlflow
```

### CLI Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--questions` | `questions.json` | Path to questions JSON file |
| `--model` | `$MODEL` from .env | LLM model identifier (e.g. `openai/gpt-4o`) |
| `--base-url` | `$OPENAI_BASE_URL` from .env | OpenAI-compatible API base URL |
| `--no-mlflow` | off | Disable MLflow logging |

### View MLflow Traces
Every interview turn is automatically logged. To view the traces and reasoning:
```bash
uv run mlflow ui
```
Then navigate to `http://localhost:5000` to see the "Interview_Bot" experiment (CLI) or "Interview_Bot_Web" (web UI). Traces include version metadata for filtering across releases.

## Testing

Run the automated test suite to verify the orchestrator and schema logic:
```bash
# On Windows (PowerShell)
$env:PYTHONPATH="."
uv run pytest

# On Linux/macOS
PYTHONPATH=. uv run pytest
```

## Architecture

- `main.py`: CLI entry point with MLflow configuration and retry logic.
- `web.py`: Gradio 6 web UI with sidebar, chat, session management, and MLflow tracing.
- `src/modules.py`: DSPy modules (using `ChainOfThought`).
- `src/signatures.py`: DSPy signatures defining the I/O schema and constraints.
- `src/orchestrator.py`: Python state management (attempts, topics, history).
- `src/schema.py`: Pydantic models for structured LLM interaction.
- `src/data.py`: Question loading with validation, and `flatten_questions()` for topic association.
- `src/session.py`: JSON file-based session persistence with server-side registry.
- `src/config.py`: Shared config loading, LLM initialization, and interview data loading.
