import json
import sys
from pathlib import Path

import jsonschema


_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "schemas" / "questions.schema.json"
)


def load_questions(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: Questions file not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"Error: Invalid JSON in {path}: {e}")

    try:
        with open(_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: Schema file not found: {_SCHEMA_PATH}")

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        sys.exit(
            f"Error: Schema validation failed in {path}: {e.message}"
            f" (at /{'/'.join(str(p) for p in e.absolute_path)})"
        )

    return data


def flatten_questions(data: dict) -> list[dict]:
    questions = []
    for topic in data["topics"]:
        for i, q in enumerate(topic["questions"], start=1):
            questions.append(
                {
                    **q,
                    "id": f"{topic['topic_id']}-{i}",
                    "topic_name": topic["topic_name"],
                }
            )
    return questions
