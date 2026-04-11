from pydantic import BaseModel, Field
from typing import Literal


class InterviewAction(BaseModel):
    model_config = {"extra": "forbid"}

    evaluation: Literal["correct", "partially_correct", "incorrect", "ambiguous"] = (
        Field(
            description=(
                "correct: fully meets criteria. Response must be a concluding statement with no follow-ups. "
                "partially_correct: on the right track but incomplete, nothing wrong. Response should ask them to elaborate on the missing parts. "
                "incorrect: doesn't meet criteria or has errors. Response should guide with a hint. "
                "ambiguous: too vague to evaluate. Response should ask for clarification."
            )
        )
    )
    reasoning: str = Field(description="Internal logic for the evaluation")
    response: str = Field(description="The message for the candidate")
