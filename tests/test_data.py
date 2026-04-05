import json
import pytest
from src.data import load_questions, flatten_questions


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


def test_load_questions_missing_file():
    with pytest.raises(SystemExit, match="Questions file not found"):
        load_questions("nonexistent_file.json")


def test_load_questions_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{invalid json")

    with pytest.raises(SystemExit, match="Invalid JSON"):
        load_questions(str(path))


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


def test_load_questions_rejects_invalid_schema(tmp_path):
    test_data = {
        "interview_id": "test",
        "topics": [{"topic_name": "T1", "questions": []}],
    }
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(test_data))

    with pytest.raises(SystemExit, match="Schema validation failed"):
        load_questions(str(path))


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
