"""Evaluation metric for InterviewBot optimization.

Rules (evaluation-as-hard-gate):
- evaluation wrong → 0.0
- evaluation correct + command correct → 1.0
- evaluation correct + command wrong → 0.5

Returns dspy.Prediction(score=float, feedback=str) for GEPA compatibility.
"""

import dspy


def evaluation_metric(
    gold: dspy.Example,
    pred: dspy.Prediction,
    trace=None,
    pred_name: str | None = None,
    pred_trace=None,
) -> dspy.Prediction:
    """Score InterviewBot predictions against expected labels.

    Evaluation is a hard gate: wrong evaluation always scores 0.0.
    """
    expected_eval = gold.expected_evaluation
    expected_cmd = gold.expected_command
    actual_action = pred.action

    eval_correct = actual_action.evaluation == expected_eval
    cmd_correct = actual_action.command == expected_cmd

    if not eval_correct:
        score = 0.0
        feedback = (
            f"Evaluation wrong. Expected '{expected_eval}', got '{actual_action.evaluation}'. "
            f"Reasoning: {actual_action.reasoning}"
        )
    elif cmd_correct:
        score = 1.0
        feedback = "Evaluation and command both correct."
    else:
        score = 0.5
        feedback = (
            f"Evaluation correct but command wrong. "
            f"Expected '{expected_cmd}', got '{actual_action.command}'. "
            f"Reasoning: {actual_action.reasoning}"
        )

    return dspy.Prediction(score=score, feedback=feedback)
