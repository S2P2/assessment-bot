import os
import sys

import dspy
from dotenv import load_dotenv

from src.data import flatten_questions, load_questions

_DEFAULT_MODEL = "openai/qwen3.5:4b"


def load_config() -> dict:
    """Load environment config. Exits if OPENAI_API_KEY is missing."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Error: OPENAI_API_KEY not found. Set it in .env or environment.")
    return {
        "api_key": api_key,
        "model": os.getenv("MODEL", _DEFAULT_MODEL),
        "base_url": os.getenv("OPENAI_BASE_URL"),
    }


def init_lm(config: dict) -> dspy.LM:
    """Create and configure the DSPy LM instance."""
    lm_args: dict = {"api_key": config["api_key"]}
    if config["base_url"]:
        lm_args["api_base"] = config["base_url"]
    lm = dspy.LM(config["model"], **lm_args)
    dspy.configure(lm=lm)
    return lm


def load_interview_data(path: str = "questions.json"):
    """Load and flatten interview questions. Returns (raw_data, flat_questions)."""
    data = load_questions(path)
    questions = flatten_questions(data)
    return data, questions
