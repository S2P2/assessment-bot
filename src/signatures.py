import dspy
from src.schema import InterviewAction, SummaryVerdict


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
        desc="Structured response including evaluation, reasoning, and the next response string. If command is NEXT_QUESTION, the response MUST be a concluding statement or transition. It MUST NOT ask follow-up questions. Use 'CLARIFY' if the user is too vague to evaluate."
    )


class InterviewSummary(dspy.Signature):
    """Generate an end-of-interview improvement summary based on the full conversation."""

    question_summaries = dspy.InputField(
        desc="List of per-question summaries with evaluation, hints used, and skip status."
    )
    conversation_history = dspy.InputField(
        desc="Full transcript of the interview (all turns between candidate and interviewer)."
    )
    verdict: SummaryVerdict = dspy.OutputField(
        desc="Structured summary with per-topic observations and an overall verdict."
    )
