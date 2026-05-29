# Assessment Bot

## Development

All Python commands must be run via `uv run`:

- `uv run pytest tests/ -v` (on Windows PowerShell: `$env:PYTHONPATH="."; uv run pytest tests/ -v`)
- `uv run ruff check src/ tests/`
- `uv run ruff format src/ tests/`

## Project Structure

- `questions.json` — interview question data (validated against `schemas/questions.schema.json`)
- `src/data.py` — loads and flattens questions with schema validation
- `src/orchestrator.py` — interview state machine
- `src/modules.py` / `src/signatures.py` — DSPy interview bot
- `src/schema.py` — Pydantic models for LLM output
- `src/report.py` — end-of-interview report generation (score, breakdown, improvement summary)
- `src/session.py` — JSON file-based session persistence
- `src/config.py` — shared config loading, LLM init, interview data loading
- `main.py` — CLI entry point
- `web.py` — Gradio 6 web UI entry point

## Agent skills

### Issue tracker

Issues tracked in GitHub Issues via `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. See `docs/agents/domain.md`.
