import pytest
from pydantic import ValidationError
from src.schema import InterviewAction


def test_interview_action_correct():
    action = InterviewAction(
        evaluation="correct",
        reasoning="User got it right.",
        response="Great job!",
    )
    assert action.evaluation == "correct"


def test_interview_action_partially_correct():
    action = InterviewAction(
        evaluation="partially_correct",
        reasoning="Right concept but missing key detail.",
        response="You're on the right track. Can you elaborate?",
    )
    assert action.evaluation == "partially_correct"


def test_interview_action_incorrect():
    action = InterviewAction(
        evaluation="incorrect",
        reasoning="Missing key concept.",
        response="Not quite.",
    )
    assert action.evaluation == "incorrect"


def test_interview_action_ambiguous():
    action = InterviewAction(
        evaluation="ambiguous",
        reasoning="Answer was vague.",
        response="Can you elaborate?",
    )
    assert action.evaluation == "ambiguous"


def test_interview_action_invalid_evaluation():
    with pytest.raises(ValidationError):
        InterviewAction(
            evaluation="excellent",
            reasoning="N/A",
            response="N/A",
        )


def test_interview_action_command_field_removed():
    """Command field no longer exists on InterviewAction."""
    with pytest.raises(ValidationError):
        InterviewAction(
            evaluation="correct",
            reasoning="N/A",
            response="N/A",
            command="NEXT_QUESTION",
        )
