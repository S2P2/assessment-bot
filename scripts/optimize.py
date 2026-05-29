"""Optimize InterviewBot using BootstrapFewShot.

Loads answer variants as labeled dspy.Examples, runs BootstrapFewShot,
and saves the compiled program.

Usage:
    uv run scripts/optimize.py [--variants PATH] [--output PATH]
"""

import argparse
import json
from pathlib import Path

import dspy

from src.config import init_lm, load_config, load_interview_data
from src.metric import evaluation_metric
from src.modules import InterviewBot

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_VARIANTS = _PROJECT_ROOT / "training" / "answer_variants.json"
_DEFAULT_OUTPUT = _PROJECT_ROOT / "training" / "optimized.json"


def load_variants(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_examples(questions: list[dict], variants: dict) -> list[dspy.Example]:
    """Convert answer variants into labeled dspy.Examples for optimization."""
    examples = []

    for question in questions:
        qid = question["id"]
        if qid not in variants["variants"]:
            continue

        for variant in variants["variants"][qid]:
            example = dspy.Example(
                topic=question["topic_name"],
                question=question["text"],
                criteria=question["criteria"],
                hint_guidelines=question["hint_guidelines"],
                history=[],
                user_input=variant["user_input"],
                attempt_number=0,
                last_evaluation="None",
                next_topic=None,
                # Gold labels — stored as expected_* on the example
                expected_evaluation=variant["expected_evaluation"],
                expected_command=variant["expected_command"],
            ).with_inputs(
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
            examples.append(example)

    return examples


def main():
    parser = argparse.ArgumentParser(description="Optimize InterviewBot")
    parser.add_argument(
        "--variants",
        default=str(_DEFAULT_VARIANTS),
        help="Path to answer variants JSON",
    )
    parser.add_argument(
        "--output", default=str(_DEFAULT_OUTPUT), help="Path to save optimized program"
    )
    args = parser.parse_args()

    # Init LM
    config = load_config()
    init_lm(config)

    # Load data
    _, questions = load_interview_data()
    variants = load_variants(args.variants)
    examples = build_examples(questions, variants)

    # Split: use all for trainset (small dataset, POC)
    trainset = examples
    print(f"Training with {len(trainset)} examples")

    # Baseline evaluation
    bot = InterviewBot()
    evaluator = dspy.Evaluate(
        devset=trainset,
        metric=evaluation_metric,
        num_threads=1,
        display_progress=True,
        display_table=5,
    )
    print("\n--- Baseline ---")
    baseline_result = evaluator(bot)
    print(f"Baseline score: {baseline_result.score:.3f}")

    # Optimize
    optimizer = dspy.BootstrapFewShot(
        metric=evaluation_metric,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )

    print("\n--- Optimizing (BootstrapFewShot) ---")
    optimized = optimizer.compile(student=bot, trainset=trainset)

    # Post-optimization evaluation
    print("\n--- Optimized ---")
    optimized_result = evaluator(optimized)
    print(f"Optimized score: {optimized_result.score:.3f}")

    delta = optimized_result.score - baseline_result.score
    print(f"Delta: {delta:+.3f}")

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    optimized.save(str(output_path), save_program=False)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
