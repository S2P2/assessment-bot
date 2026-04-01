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
    action: InterviewAction = dspy.OutputField(desc="Structured response including evaluation, reasoning, and the next response string. If correct, set command to NEXT_QUESTION and provide a transition. If incorrect, set command to GIVE_HINT and provide a nudge based on guidelines without revealing the criteria keywords.")
