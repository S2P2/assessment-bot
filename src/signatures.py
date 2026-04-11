import dspy
from src.schema import InterviewAction


class InterviewTurn(dspy.Signature):
    """Evaluate candidate answer and generate the next interviewer response."""

    topic = dspy.InputField()
    question = dspy.InputField()
    criteria = dspy.InputField()
    hint_guidelines = dspy.InputField()
    history = dspy.InputField(desc="Previous turns as a list of strings")
    user_input = dspy.InputField()
    attempt_number = dspy.InputField()
    last_evaluation = dspy.InputField(
        desc="The evaluation result from the previous turn, or 'None' if first turn."
    )
    next_topic = dspy.InputField(desc="Name of the next topic, or None if finishing.")
    action: InterviewAction = dspy.OutputField(
        desc="Structured response with evaluation (correct/partially_correct/incorrect/ambiguous), reasoning, and the next response string."
    )
