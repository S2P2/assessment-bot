# DSPy Interview Bot POC

A terminal-based IT skill interview chatbot built with the **DSPy framework**. It uses a Unified Predictor model to evaluate answers and generate responses in a single LLM call, while a Python Orchestrator manages the conversation state.

## Features

- **Unified Logic**: Evaluation and response generation handled in a single structured LLM call.
- **Structured Output**: Uses Pydantic models to ensure consistent evaluation and command logic.
- **Orchestration**: Manages question progression, attempt limits (max 2 hints), and conversation history.
- **Customizable**: Support for custom OpenAI `base_url` and `.env` configuration.
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
   ```

## Usage

Run the interview bot:
```bash
uv run python main.py
```

## Testing

Run the automated test suite:
```bash
# On Windows (PowerShell)
$env:PYTHONPATH="."
uv run pytest

# On Linux/macOS
PYTHONPATH=. uv run pytest
```

## Architecture

- `main.py`: Entry point and CLI loop.
- `src/modules.py`: DSPy modules (Interviewer logic).
- `src/signatures.py`: DSPy signatures defining the I/O schema.
- `src/orchestrator.py`: Python state management.
- `src/schema.py`: Pydantic models for structured LLM interaction.
- `src/data.py`: Question loading utility.
