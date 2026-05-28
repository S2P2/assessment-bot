from pydantic import BaseModel, Field
from typing import Literal


class InterviewAction(BaseModel):
    evaluation: Literal["correct", "incorrect", "ambiguous"] = Field(
        description="Evaluation result"
    )
    reasoning: str = Field(description="Internal logic for the evaluation")
    response: str = Field(description="The actual message for the candidate")
    command: Literal["NEXT_QUESTION", "GIVE_HINT", "PROMPT_SKIP", "CLARIFY"] = Field(
        description="Instruction to the orchestrator. Use 'CLARIFY' if the user is too vague to evaluate (e.g., 'write good code' or 'it depends') but is not technically incorrect."
    )


class TopicObservation(BaseModel):
    topic: str = Field(description="Topic name")
    strengths: str = Field(description="What the candidate demonstrated well in this topic")
    weaknesses: str = Field(description="What the candidate struggled with or needs to improve")


class SummaryVerdict(BaseModel):
    topic_observations: list[TopicObservation] = Field(
        description="Per-topic assessment of the candidate's performance"
    )
    overall_verdict: str = Field(
        description="A one-line overall assessment (e.g. 'Solid fundamentals, needs more SQL practice.')"
    )
