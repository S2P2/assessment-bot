import pytest
from pydantic import ValidationError
from src.schema import InterviewAction


def test_interview_action_correct():
    action = InterviewAction(
        evaluation="correct",
        reasoning="User got it right.",
        response="Great job!",
        command="NEXT_QUESTION",
    )
    assert action.evaluation == "correct"


def test_interview_action_incorrect():
    action = InterviewAction(
        evaluation="incorrect",
        reasoning="Missing key concept.",
        response="Not quite.",
        command="GIVE_HINT",
    )
    assert action.evaluation == "incorrect"


def test_interview_action_ambiguous():
    action = InterviewAction(
        evaluation="ambiguous",
        reasoning="Answer was vague.",
        response="Can you elaborate?",
        command="CLARIFY",
    )
    assert action.evaluation == "ambiguous"


def test_interview_action_prompt_skip():
    action = InterviewAction(
        evaluation="incorrect",
        reasoning="Max attempts reached.",
        response="Let's move on.",
        command="PROMPT_SKIP",
    )
    assert action.command == "PROMPT_SKIP"


def test_interview_action_invalid_evaluation():
    with pytest.raises(ValidationError):
        InterviewAction(
            evaluation="excellent",
            reasoning="N/A",
            response="N/A",
            command="NEXT_QUESTION",
        )


def test_interview_action_invalid_command():
    with pytest.raises(ValidationError):
        InterviewAction(
            evaluation="correct",
            reasoning="N/A",
            response="N/A",
            command="SKIP",
        )
