"""Collect training data by running InterviewBot against answer variants.

Loads questions from questions.json and variants from training/answer_variants.json.
Runs InterviewBot with each variant's user_input and logs actual vs expected outputs.

Usage:
    uv run scripts/collect_training_data.py [--output OUTPUT_PATH]
"""

import argparse
import json
from pathlib import Path

from src.config import init_lm, load_config, load_interview_data
from src.modules import InterviewBot

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_VARIANTS = _PROJECT_ROOT / "training" / "answer_variants.json"
_DEFAULT_OUTPUT = _PROJECT_ROOT / "training" / "collected_data.json"


def load_variants(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_bot_inputs(question: dict, variant: dict) -> dict:
    """Build the kwargs dict for InterviewBot.forward()."""
    return {
        "topic": question["topic_name"],
        "question": question["text"],
        "criteria": question["criteria"],
        "hint_guidelines": question["hint_guidelines"],
        "history": [],
        "user_input": variant["user_input"],
        "attempt_number": 0,
        "last_evaluation": "None",
        "next_topic": None,
    }


def collect(bot: InterviewBot, questions: list[dict], variants: dict) -> list[dict]:
    """Run bot against all variants, return list of result dicts."""
    results = []

    for question in questions:
        qid = question["id"]
        if qid not in variants["variants"]:
            print(f"  Skipping {qid}: no variants found")
            continue

        for variant in variants["variants"][qid]:
            inputs = build_bot_inputs(question, variant)
            print(f"  {qid} [{variant['variant_type']}]: ", end="", flush=True)

            try:
                pred = bot(**inputs)
                actual = pred.action

                result = {
                    "question_id": qid,
                    "variant_type": variant["variant_type"],
                    "user_input": variant["user_input"],
                    "expected_evaluation": variant["expected_evaluation"],
                    "expected_command": variant["expected_command"],
                    "actual_evaluation": actual.evaluation,
                    "actual_command": actual.command,
                    "actual_reasoning": actual.reasoning,
                    "actual_response": actual.response,
                    "eval_match": actual.evaluation == variant["expected_evaluation"],
                    "cmd_match": actual.command == variant["expected_command"],
                }

                match_str = "✓" if result["eval_match"] else "✗"
                print(f"eval={actual.evaluation} cmd={actual.command} {match_str}")

            except Exception as e:
                print(f"ERROR: {e}")
                result = {
                    "question_id": qid,
                    "variant_type": variant["variant_type"],
                    "user_input": variant["user_input"],
                    "expected_evaluation": variant["expected_evaluation"],
                    "expected_command": variant["expected_command"],
                    "error": str(e),
                }

            results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Collect InterviewBot training data")
    parser.add_argument(
        "--variants",
        default=str(_DEFAULT_VARIANTS),
        help="Path to answer variants JSON",
    )
    parser.add_argument(
        "--output", default=str(_DEFAULT_OUTPUT), help="Path to write collected data"
    )
    args = parser.parse_args()

    # Init LM
    config = load_config()
    init_lm(config)

    # Load data
    _, questions = load_interview_data()
    variants = load_variants(args.variants)

    print(
        f"Loaded {len(questions)} questions, "
        f"{sum(len(v) for v in variants['variants'].values())} variants"
    )

    # Run collection
    bot = InterviewBot()
    results = collect(bot, questions, variants)

    # Summary
    eval_matches = sum(1 for r in results if r.get("eval_match"))
    cmd_matches = sum(1 for r in results if r.get("cmd_match"))
    errors = sum(1 for r in results if "error" in r)
    total = len(results)

    print("\n--- Summary ---")
    print(f"Total: {total}")
    print(f"Eval match: {eval_matches}/{total} ({eval_matches / total:.0%})")
    print(f"Cmd match:  {cmd_matches}/{total} ({cmd_matches / total:.0%})")
    print(f"Errors:     {errors}")

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
