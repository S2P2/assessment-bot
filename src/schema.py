from pydantic import BaseModel, Field
from typing import Literal

class InterviewAction(BaseModel):
    evaluation: Literal["correct", "incorrect", "ambiguous"] = Field(description="Evaluation result")
    reasoning: str = Field(description="Internal logic for the evaluation")
    response: str = Field(description="The actual message for the candidate")
    command: Literal["NEXT_QUESTION", "GIVE_HINT", "PROMPT_SKIP"] = Field(description="Instruction to the orchestrator")
