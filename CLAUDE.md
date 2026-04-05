# Assessment Bot

## Development

All Python commands must be run via `uv run`:

- `uv run pytest tests/ -v`
- `uv run ruff check src/ tests/`
- `uv run ruff format src/ tests/`

## Project Structure

- `questions.json` — interview question data (validated against `schemas/questions.schema.json`)
- `src/data.py` — loads and flattens questions with schema validation
- `src/orchestrator.py` — interview state machine
- `src/modules.py` / `src/signatures.py` — DSPy interview bot
- `src/schema.py` — Pydantic models for LLM output
- `main.py` — CLI entry point
