import dspy
from src.signatures import InterviewTurn, InterviewSummary


class InterviewBot(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(InterviewTurn)

    def forward(self, **kwargs):
        return self.predictor(**kwargs)


class SummaryBot(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(InterviewSummary)

    def forward(self, **kwargs):
        return self.predictor(**kwargs)
