import dspy
from src.signatures import InterviewTurn

class InterviewBot(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predictor = dspy.Predict(InterviewTurn)

    def forward(self, **kwargs):
        return self.predictor(**kwargs)
