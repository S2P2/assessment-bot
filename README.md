# DSPy Interview Bot POC (v0.3.2)

A terminal-based IT skill interview chatbot built with the **DSPy framework**. It uses a Unified Predictor model with **Chain of Thought** reasoning to evaluate answers and generate responses in a single LLM call, while a Python Orchestrator manages the rigid conversation state.

## New in v0.3.1

- **Detailed Interaction Tracking**: The `InterviewOrchestrator` now provides granular tracking of `turns_in_question`, `hints_given`, and `clarifications_requested`, allowing for deeper session analytics.
- **Evaluation History**: The LLM now receives the `last_evaluation` result, providing context for the current turn (e.g., whether the user was just asked to clarify their previous answer).
- **Session Summaries**: Every question session is summarized into `question_summaries`, capturing final evaluations, total turns, and skip reasons for persistent reporting.

## New in v0.3.0

- **Ambiguity Handling (`CLARIFY`)**: A new command that allows the LLM to ask for more detail when an answer is too vague (e.g., "write good code") without penalizing the candidate's attempt counter.
- **MLflow Observability**: Native integration with MLflow for automatic tracing of DSPy calls. This captures reasoning steps, inputs, and outputs for every turn.
- **Topic Awareness**: The bot is now aware of upcoming topics, allowing for smoother transitions (e.g., "Great! Now let's move on to Python Basics").
- **Improved UI**: To reduce clutter, the full question text is only printed on the first attempt. During hints and clarifications, only the interviewer's nudge is shown.

## Features

- **Unified Logic**: Evaluation and response generation handled in a single structured call using `dspy.ChainOfThought`.
- **Structured Output**: Uses Pydantic models in `src/schema.py` to ensure consistent evaluation and command logic.
- **Orchestration**: Manages question progression, attempt limits (max 2 hints), and conversation history in `src/orchestrator.py`.
- **Customizable**: Full support for custom OpenAI `base_url`, configurable model, and `.env` files.
- **MLflow Tracing**: Every turn is traced with user/session metadata and named spans (`{topic}: {question_id}`) for easy filtering.
- **Resilient**: Retries on transient LLM failures, exits cleanly on Ctrl+C, and gives clear error messages for missing config or data files.
- **Modern Tooling**: Managed with `uv` for fast, reproducible Python environments.

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

### Run the Interview Bot
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
Then navigate to `http://localhost:5000` to see the "Interview_Bot" experiment. Traces include version metadata for filtering across releases.

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

- `main.py`: Entry point, CLI loop, MLflow configuration, and retry logic.
- `src/modules.py`: DSPy modules (using `ChainOfThought`).
- `src/signatures.py`: DSPy signatures defining the I/O schema and constraints.
- `src/orchestrator.py`: Python state management (attempts, topics, history).
- `src/schema.py`: Pydantic models for structured LLM interaction.
- `src/data.py`: Question loading with validation, and `flatten_questions()` for topic association.
