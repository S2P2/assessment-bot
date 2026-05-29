"""Tests for the evaluation metric.

Metric rules (from handoff doc):
- evaluation wrong → 0.0
- evaluation correct + command correct → 1.0
- evaluation correct + command wrong → 0.5
"""

import dspy

from src.metric import evaluation_metric
from src.schema import InterviewAction


def _make_gold(expected_evaluation: str, expected_command: str) -> dspy.Example:
    return dspy.Example(
        expected_evaluation=expected_evaluation,
        expected_command=expected_command,
    ).with_inputs(
        "topic",
        "question",
        "criteria",
        "hint_guidelines",
        "history",
        "user_input",
        "attempt_number",
        "last_evaluation",
        "next_topic",
    )


def _make_pred(evaluation: str, command: str) -> dspy.Prediction:
    action = InterviewAction(
        evaluation=evaluation,
        reasoning="test reasoning",
        response="test response",
        command=command,
    )
    return dspy.Prediction(action=action)


class TestEvaluationMetric:
    """Evaluation-as-hard-gate metric tests."""

    def test_wrong_evaluation_returns_zero(self):
        """Evaluation wrong → 0.0 regardless of command."""
        gold = _make_gold("correct", "NEXT_QUESTION")
        pred = _make_pred("incorrect", "NEXT_QUESTION")
        result = evaluation_metric(gold, pred)
        assert float(result) == 0.0

    def test_both_correct_returns_one(self):
        """Evaluation correct + command correct → 1.0."""
        gold = _make_gold("correct", "NEXT_QUESTION")
        pred = _make_pred("correct", "NEXT_QUESTION")
        result = evaluation_metric(gold, pred)
        assert float(result) == 1.0

    def test_eval_correct_command_wrong_returns_half(self):
        """Evaluation correct + command wrong → 0.5."""
        gold = _make_gold("correct", "NEXT_QUESTION")
        pred = _make_pred("correct", "GIVE_HINT")
        result = evaluation_metric(gold, pred)
        assert float(result) == 0.5

    def test_ambiguous_eval_correct(self):
        """Ambiguous matches ambiguous — both correct → 1.0."""
        gold = _make_gold("ambiguous", "CLARIFY")
        pred = _make_pred("ambiguous", "CLARIFY")
        result = evaluation_metric(gold, pred)
        assert float(result) == 1.0

    def test_returns_prediction_with_feedback(self):
        """Metric returns dspy.Prediction with score and feedback."""
        gold = _make_gold("correct", "NEXT_QUESTION")
        pred = _make_pred("correct", "NEXT_QUESTION")
        result = evaluation_metric(gold, pred)
        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, "feedback")
        assert isinstance(result.feedback, str)
        assert len(result.feedback) > 0
