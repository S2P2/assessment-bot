from src.schema import InterviewAction
import pytest

def test_interview_action_validation():
    data = {
        "evaluation": "correct",
        "reasoning": "User got it right.",
        "response": "Great job!",
        "command": "NEXT_QUESTION"
    }
    action = InterviewAction(**data)
    assert action.evaluation == "correct"
