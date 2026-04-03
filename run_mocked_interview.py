from unittest.mock import patch, MagicMock
from src.schema import InterviewAction
import main


# Mock result to match DSPy output
class MockResult:
    def __init__(self, action):
        self.action = action


# Mock bot that returns a valid InterviewAction
class MockBot:
    def __call__(self, **kwargs):
        # Always progress to next question for simplicity
        return MockResult(
            InterviewAction(
                evaluation="correct",
                reasoning="Mocked logic: user was correct",
                response="That's correct! Let's move on.",
                command="NEXT_QUESTION",
            )
        )


# Simulated inputs: Username, then one answer for each of the 3 questions
simulated_inputs = [
    "test_user",
    "I would use DISTINCT.",
    "INNER vs LEFT.",
    "try-except.",
]


def run_mocked():
    # Monkey-patch InterviewBot in the main module
    with patch("main.InterviewBot", side_effect=lambda: MockBot()):
        # Mock dspy.LM so it doesn't try to connect
        with patch("dspy.LM", return_value=MagicMock()):
            # Mock dspy.configure to do nothing
            with patch("dspy.configure"):
                # Mock input() to provide our simulated answers
                with patch("builtins.input", side_effect=simulated_inputs):
                    main.main()


if __name__ == "__main__":
    run_mocked()
