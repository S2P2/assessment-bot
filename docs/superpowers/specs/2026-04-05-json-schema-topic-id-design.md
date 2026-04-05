# JSON Schema + Topic ID + Computed Question IDs

**Date:** 2026-04-05
**Status:** Draft

## Goal

Add structural validation to `questions.json` via JSON Schema, introduce `topic_id` on each topic, and derive question IDs from topic IDs at load time instead of manually maintaining them.

## Approach

Minimal: JSON Schema for validation, computed IDs in `flatten_questions`. No Pydantic models for the config file.

## Changes

### 1. New file: `schemas/questions.schema.json`

Draft 2020-12 JSON Schema enforcing:

- Top level: `interview_id` (string), `topics` (array)
- Each topic requires: `topic_id` (string, pattern `^[a-z][a-z0-9-]*$`), `topic_name` (string), `questions` (array, minItems 1)
- Each question requires: `text` (string), `criteria` (string), `hint_guidelines` (string)
- Question objects use `additionalProperties: false` — no `id` field allowed

The `topic_id` pattern ensures lowercase, letter-start, alphanumeric + dashes only — safe for computed IDs.

### 2. `questions.json` updates

- Add `topic_id` to each topic (e.g., `"sql"`, `"python"`)
- Remove `id` from each question
- Keep `text`, `criteria`, `hint_guidelines` unchanged

### 3. `src/data.py` changes

**`load_questions`:**
- Load schema from `schemas/questions.schema.json`
- Call `jsonschema.validate(data, schema)` after JSON parsing
- Wrap `ValidationError` into a clear error message with path and issue

**`flatten_questions`:**
- For each topic, read `topic_id`
- For each question in that topic, assign `id = f"{topic_id}-{i+1}"` (1-indexed within topic)
- Still inject `topic_name` as before

### 4. Dependencies

- Add `jsonschema` as a direct dependency in `pyproject.toml` (already installed transitively)

### 5. Test updates

**`tests/test_data.py`:**
- Remove `id` from question fixtures, add `topic_id` to topic fixtures
- Update `flatten_questions` assertions to expect computed IDs (`sql-1`, `sql-2`, `python-1`)
- Add test: valid data passes schema validation
- Add test: invalid data (missing required field, extra property) raises with clear message
- Update `test_flatten_questions_does_not_mutate_original` for new structure

**`tests/test_orchestrator.py`:** No changes needed — orchestrator consumes flat lists with pre-computed IDs.

### 6. No changes needed

- `src/orchestrator.py` — reads `q.get("id")` from flat list, works with any ID format
- `src/modules.py` — no awareness of question structure
- `src/signatures.py` — no awareness of question structure
- `main.py` — uses `q['id']` in MLflow span names, works with computed IDs

## Example: Updated `questions.json`

```json
{
  "interview_id": "it-skill-eval-v1",
  "topics": [
    {
      "topic_id": "sql",
      "topic_name": "SQL Basics",
      "questions": [
        {
          "text": "How do you find unique values in a column?",
          "criteria": "Must use the DISTINCT keyword.",
          "hint_guidelines": "Nudge them toward the concept of uniqueness without saying 'DISTINCT' directly."
        },
        {
          "text": "What is the difference between an INNER JOIN and a LEFT JOIN?",
          "criteria": "Must explain that INNER JOIN returns only matching rows, while LEFT JOIN returns all rows from the left table regardless of matches.",
          "hint_guidelines": "Ask what happens to rows in the first table if there is no matching entry in the second."
        }
      ]
    },
    {
      "topic_id": "python",
      "topic_name": "Python Basics",
      "questions": [
        {
          "text": "How do you handle exceptions in Python to prevent the program from crashing?",
          "criteria": "Must explicitly mention 'try' and 'except' blocks.",
          "hint_guidelines": "Ask about the block-based structure used to catch errors during execution."
        }
      ]
    }
  ]
}
```

After `flatten_questions`, questions get IDs: `sql-1`, `sql-2`, `python-1`.
