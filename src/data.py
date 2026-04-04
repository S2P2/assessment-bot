import json
import sys


def load_questions(path: str):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: Questions file not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"Error: Invalid JSON in {path}: {e}")


def flatten_questions(data: dict) -> list[dict]:
    questions = []
    for topic in data["topics"]:
        for q in topic["questions"]:
            questions.append({**q, "topic_name": topic["topic_name"]})
    return questions
