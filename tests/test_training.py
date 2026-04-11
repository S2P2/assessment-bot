import json
import pytest
from src.training import load_training_data, to_examples


def test_load_training_data(tmp_path):
    data = [
        {
            "topic": "SQL",
            "question": "Q1",
            "criteria": "c1",
            "hint_guidelines": "h1",
            "history": [],
            "user_input": "answer",
            "attempt_number": 0,
            "last_evaluation": "None",
            "next_topic": "SQL",
            "action": {
                "evaluation": "correct",
                "reasoning": "Right",
                "response": "Good!",
            },
        }
    ]
    path = tmp_path / "train.json"
    path.write_text(json.dumps(data))

    result = load_training_data(str(path))
    assert len(result) == 1
    assert result[0]["action"]["evaluation"] == "correct"


def test_load_training_data_missing_file():
    with pytest.raises(FileNotFoundError):
        load_training_data("nonexistent.json")


def test_load_training_data_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{invalid}")
    with pytest.raises(json.JSONDecodeError):
        load_training_data(str(path))


def test_to_examples():
    data = [
        {
            "topic": "SQL",
            "question": "Q1",
            "criteria": "c1",
            "hint_guidelines": "h1",
            "history": [],
            "user_input": "answer",
            "attempt_number": 0,
            "last_evaluation": "None",
            "next_topic": "SQL",
            "action": {
                "evaluation": "correct",
                "reasoning": "Right",
                "response": "Good!",
            },
        }
    ]
    examples = to_examples(data)
    assert len(examples) == 1

    # Verify inputs are marked correctly
    inputs = examples[0].inputs()
    assert hasattr(inputs, "topic")
    assert hasattr(inputs, "question")
    assert hasattr(inputs, "criteria")

    # Verify labels contain the action
    labels = examples[0].labels()
    assert hasattr(labels, "action")


def test_to_examples_uses_real_data():
    """Verify the actual training file loads and converts."""
    data = load_training_data("data/training/sql_examples.json")
    examples = to_examples(data)
    assert len(examples) == 20