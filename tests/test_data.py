import pytest
import os
import json
from src.data import load_questions

def test_load_questions_valid():
    test_data = {"interview_id": "test", "topics": [{"topic_name": "T1", "questions": []}]}
    with open("test_questions.json", "w") as f:
        json.dump(test_data, f)
    
    try:
        data = load_questions("test_questions.json")
        assert data["interview_id"] == "test"
    finally:
        if os.path.exists("test_questions.json"):
            os.remove("test_questions.json")
