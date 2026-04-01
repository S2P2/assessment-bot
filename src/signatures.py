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
    next_topic = dspy.InputField(desc="Name of the next topic, or None if finishing.")
    action: InterviewAction = dspy.OutputField(desc="Structured response including evaluation, reasoning, and the next response string. If command is NEXT_QUESTION, the response MUST be a concluding statement or transition. It MUST NOT ask follow-up questions. Use 'CLARIFY' if the user is too vague to evaluate.")
