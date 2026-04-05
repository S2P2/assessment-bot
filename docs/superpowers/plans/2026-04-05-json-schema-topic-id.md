# JSON Schema + Topic ID + Computed Question IDs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JSON Schema validation to `questions.json`, introduce `topic_id`, and compute question IDs from topic IDs at load time.

**Architecture:** A new `schemas/questions.schema.json` file defines the structural contract. `src/data.py` gains schema validation in `load_questions` and computed IDs in `flatten_questions`. The `questions.json` data file drops `id` fields and adds `topic_id`. Downstream code (orchestrator, main) needs no changes.

**Tech Stack:** `jsonschema` (already a transitive dependency, promoted to direct), Python 3.13, pytest.

---

### Task 1: Add `jsonschema` as a direct dependency

**Files:**
- Modify: `pyproject.toml:8`

- [ ] **Step 1: Add `jsonschema` to dependencies in `pyproject.toml`**

In `pyproject.toml`, add `"jsonschema>=4.23.0"` to the `dependencies` list, alphabetically after `"dspy"`:

```toml
dependencies = [
    "dspy>=3.1.3",
    "jsonschema>=4.23.0",
    "mlflow>=3.10.1",
    "openai>=2.30.0",
    "pydantic>=2.12.5",
    "pytest>=9.0.2",
    "python-dotenv>=1.2.2",
]
```

- [ ] **Step 2: Sync the lockfile**

Run: `uv lock`
Expected: lockfile updated with `jsonschema` as a direct dependency.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add jsonschema as direct dependency"
```

---

### Task 2: Create the JSON Schema file

**Files:**
- Create: `schemas/questions.schema.json`

- [ ] **Step 1: Create `schemas/` directory and schema file**

```bash
mkdir -p schemas
```

Create `schemas/questions.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "InterviewQuestions",
  "type": "object",
  "required": ["interview_id", "topics"],
  "additionalProperties": false,
  "properties": {
    "interview_id": {
      "type": "string",
      "minLength": 1
    },
    "topics": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["topic_id", "topic_name", "questions"],
        "additionalProperties": false,
        "properties": {
          "topic_id": {
            "type": "string",
            "pattern": "^[a-z][a-z0-9-]*$"
          },
          "topic_name": {
            "type": "string",
            "minLength": 1
          },
          "questions": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "required": ["text", "criteria", "hint_guidelines"],
              "additionalProperties": false,
              "properties": {
                "text": {
                  "type": "string",
                  "minLength": 1
                },
                "criteria": {
                  "type": "string",
                  "minLength": 1
                },
                "hint_guidelines": {
                  "type": "string",
                  "minLength": 1
                }
              }
            }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add schemas/questions.schema.json
git commit -m "feat: add JSON Schema for questions.json validation"
```

---

### Task 3: Update `questions.json` to match the new schema

**Files:**
- Modify: `questions.json`

- [ ] **Step 1: Replace `questions.json` with new structure**

Remove `id` from each question, add `topic_id` to each topic:

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
          "criteria": "Must explicitly mention 'try' and 'except' blocks. Note: 'catch' is incorrect syntax in Python.",
          "hint_guidelines": "Ask about the block-based structure used to catch errors during execution."
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add questions.json
git commit -m "refactor: add topic_id, remove manual question IDs"
```

---

### Task 4: Add schema validation to `load_questions`

**Files:**
- Modify: `src/data.py`
- Modify: `tests/test_data.py`

- [ ] **Step 1: Write failing test for schema validation — valid data passes**

In `tests/test_data.py`, add a new test:

```python
def test_load_questions_validates_against_schema(tmp_path):
    test_data = {
        "interview_id": "test",
        "topics": [
            {
                "topic_id": "sql",
                "topic_name": "SQL",
                "questions": [
                    {
                        "text": "Q1",
                        "criteria": "must answer",
                        "hint_guidelines": "nudge",
                    }
                ],
            }
        ],
    }
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(test_data))

    data = load_questions(str(path))
    assert data["interview_id"] == "test"
```

- [ ] **Step 2: Write failing test for schema validation — invalid data raises**

In `tests/test_data.py`, add a test that missing `topic_id` is caught:

```python
def test_load_questions_rejects_invalid_schema(tmp_path):
    test_data = {
        "interview_id": "test",
        "topics": [{"topic_name": "T1", "questions": []}],
    }
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(test_data))

    with pytest.raises(SystemExit, match="Schema validation failed"):
        load_questions(str(path))
```

Add a test that an extra property on a question is caught:

```python
def test_load_questions_rejects_extra_properties(tmp_path):
    test_data = {
        "interview_id": "test",
        "topics": [
            {
                "topic_id": "sql",
                "topic_name": "SQL",
                "questions": [
                    {
                        "text": "Q1",
                        "criteria": "must answer",
                        "hint_guidelines": "nudge",
                        "id": "q1",
                    }
                ],
            }
        ],
    }
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(test_data))

    with pytest.raises(SystemExit, match="Schema validation failed"):
        load_questions(str(path))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_data.py -v`
Expected: `test_load_questions_validates_against_schema` PASSES (schema validation not yet enforced). `test_load_questions_rejects_invalid_schema` and `test_load_questions_rejects_extra_properties` PASS (because validation not yet added — these test the future behavior).

Actually, since validation is not yet in `load_questions`, all three will pass because `load_questions` doesn't validate yet. The invalid-schema test will fail once we add validation. Skip this step — the tests are written to describe desired behavior. They will be verified after implementation.

- [ ] **Step 4: Implement schema validation in `load_questions`**

Replace `src/data.py` with:

```python
import json
import sys
from pathlib import Path

import jsonschema


_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "questions.schema.json"


def load_questions(path: str):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: Questions file not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"Error: Invalid JSON in {path}: {e}")

    try:
        with open(_SCHEMA_PATH, "r") as f:
            schema = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: Schema file not found: {_SCHEMA_PATH}")

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        sys.exit(f"Error: Schema validation failed in {path}: {e.message} (at /{'/'.join(str(p) for p in e.absolute_path)})")

    return data


def flatten_questions(data: dict) -> list[dict]:
    questions = []
    for topic in data["topics"]:
        for i, q in enumerate(topic["questions"], start=1):
            questions.append({**q, "id": f"{topic['topic_id']}-{i}", "topic_name": topic["topic_name"]})
    return questions
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_data.py -v`
Expected: All tests pass, including the two new schema rejection tests.

- [ ] **Step 6: Commit**

```bash
git add src/data.py tests/test_data.py
git commit -m "feat: add schema validation and computed question IDs"
```

---

### Task 5: Update existing tests for new data structure

**Files:**
- Modify: `tests/test_data.py`

- [ ] **Step 1: Update `test_flatten_questions` for computed IDs**

Replace `test_flatten_questions` with:

```python
def test_flatten_questions():
    data = {
        "interview_id": "test",
        "topics": [
            {
                "topic_id": "sql",
                "topic_name": "SQL",
                "questions": [
                    {"text": "Q1", "criteria": "c1", "hint_guidelines": "h1"},
                    {"text": "Q2", "criteria": "c2", "hint_guidelines": "h2"},
                ],
            },
            {
                "topic_id": "python",
                "topic_name": "Python",
                "questions": [
                    {"text": "Q3", "criteria": "c3", "hint_guidelines": "h3"},
                ],
            },
        ],
    }
    result = flatten_questions(data)

    assert len(result) == 3
    assert result[0] == {
        "text": "Q1",
        "criteria": "c1",
        "hint_guidelines": "h1",
        "id": "sql-1",
        "topic_name": "SQL",
    }
    assert result[1] == {
        "text": "Q2",
        "criteria": "c2",
        "hint_guidelines": "h2",
        "id": "sql-2",
        "topic_name": "SQL",
    }
    assert result[2] == {
        "text": "Q3",
        "criteria": "c3",
        "hint_guidelines": "h3",
        "id": "python-1",
        "topic_name": "Python",
    }
```

- [ ] **Step 2: Update `test_flatten_questions_does_not_mutate_original`**

Replace with:

```python
def test_flatten_questions_does_not_mutate_original():
    data = {
        "interview_id": "test",
        "topics": [
            {
                "topic_id": "sql",
                "topic_name": "SQL",
                "questions": [
                    {"text": "Q1", "criteria": "c1", "hint_guidelines": "h1"}
                ],
            },
        ],
    }
    original_q = data["topics"][0]["questions"][0].copy()
    flatten_questions(data)

    assert "id" not in data["topics"][0]["questions"][0]
    assert "topic_name" not in data["topics"][0]["questions"][0]
    assert data["topics"][0]["questions"][0] == original_q
```

- [ ] **Step 3: Update `test_load_questions_valid` for new structure**

Replace with:

```python
def test_load_questions_valid(tmp_path):
    test_data = {
        "interview_id": "test",
        "topics": [
            {
                "topic_id": "sql",
                "topic_name": "SQL",
                "questions": [
                    {
                        "text": "Q1",
                        "criteria": "must answer",
                        "hint_guidelines": "nudge",
                    }
                ],
            }
        ],
    }
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(test_data))

    data = load_questions(str(path))
    assert data["interview_id"] == "test"
```

- [ ] **Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_data.py
git commit -m "test: update fixtures for topic_id and computed question IDs"
```

---

### Task 6: Verify end-to-end with linters

**Files:** None

- [ ] **Step 1: Run linters**

Run: `ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: No errors or formatting issues.

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass, including orchestrator tests (which are unaffected).

- [ ] **Step 3: Verify `load_questions` rejects bad `topic_id` patterns**

Quick manual check — add a temporary test or run:

```bash
python -c "
import json, sys
sys.path.insert(0, '.')
from src.data import load_questions
import tempfile, os

bad = json.dumps({
    'interview_id': 'test',
    'topics': [{'topic_id': 'BAD', 'topic_name': 'T', 'questions': [{'text': 'Q', 'criteria': 'C', 'hint_guidelines': 'H'}]}]
})
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    f.write(bad)
    path = f.name
try:
    load_questions(path)
    print('FAIL: should have exited')
except SystemExit as e:
    print(f'OK: {e}')
finally:
    os.unlink(path)
"
```

Expected: `OK: Error: Schema validation failed ...`

- [ ] **Step 4: Final commit if any lint fixes were needed**

```bash
git add -A
git commit -m "chore: lint fixes from schema migration"
```
