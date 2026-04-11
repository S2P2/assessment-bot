import json

import dspy

from src.schema import InterviewAction


def load_training_data(path: str) -> list[dict]:
    """Load training examples from a JSON file."""
    with open(path) as f:
        return json.load(f)


def to_examples(data: list[dict]) -> list[dspy.Example]:
    """Convert raw training dicts to dspy.Example objects."""
    input_fields = (
        "topic",
        "question",
        "criteria",
        "hint_guidelines",
        "history",
        "user_input",
        "attempt_number",
        "last_evaluation",
        "next_topic",
    )
    examples = []
    for item in data:
        action = InterviewAction(**item["action"])
        example = dspy.Example(
            topic=item["topic"],
            question=item["question"],
            criteria=item["criteria"],
            hint_guidelines=item["hint_guidelines"],
            history=item["history"],
            user_input=item["user_input"],
            attempt_number=item["attempt_number"],
            last_evaluation=item["last_evaluation"],
            next_topic=item["next_topic"],
            action=action,
        ).with_inputs(*input_fields)
        examples.append(example)
    return examples
