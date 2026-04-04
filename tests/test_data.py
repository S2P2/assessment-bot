import json
import pytest
from src.data import load_questions, flatten_questions


def test_load_questions_valid(tmp_path):
    test_data = {"interview_id": "test", "topics": [{"topic_name": "T1", "questions": []}]}
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
            {"topic_name": "SQL", "questions": [
                {"id": "q1", "text": "Q1"},
                {"id": "q2", "text": "Q2"},
            ]},
            {"topic_name": "Python", "questions": [
                {"id": "q3", "text": "Q3"},
            ]},
        ],
    }
    result = flatten_questions(data)

    assert len(result) == 3
    assert result[0] == {"id": "q1", "text": "Q1", "topic_name": "SQL"}
    assert result[1] == {"id": "q2", "text": "Q2", "topic_name": "SQL"}
    assert result[2] == {"id": "q3", "text": "Q3", "topic_name": "Python"}


def test_flatten_questions_does_not_mutate_original():
    data = {
        "interview_id": "test",
        "topics": [
            {"topic_name": "SQL", "questions": [{"id": "q1", "text": "Q1"}]},
        ],
    }
    original_q = data["topics"][0]["questions"][0].copy()
    flatten_questions(data)

    assert "topic_name" not in data["topics"][0]["questions"][0]
    assert data["topics"][0]["questions"][0] == original_q
