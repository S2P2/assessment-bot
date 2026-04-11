"""DSPy optimization runner.

Compiles InterviewBot using BootstrapFewShot and MIPROv2 optimizers
against hand-crafted SQL training data.

Usage:
    PYTHONPATH=. OPENAI_API_KEY=your-key uv run python scripts/optimize.py
"""

import dspy

from src.config import init_lm, load_config
from src.modules import InterviewBot
from src.training import load_training_data, to_examples


def evaluation_accuracy(example, prediction, trace=None):
    """Score 1.0 if evaluation matches the gold label."""
    return 1.0 if example.action.evaluation == prediction.action.evaluation else 0.0


def main():
    config = load_config()
    init_lm(config)

    # Load and split training data (80/20)
    data = load_training_data("data/training/sql_examples.json")
    examples = to_examples(data)
    split = int(len(examples) * 0.8)
    trainset = examples[:split]
    valset = examples[split:]

    print(f"Training: {len(trainset)} examples, Validation: {len(valset)} examples")

    # Phase 1: BootstrapFewShot baseline
    print("\n=== Phase 1: BootstrapFewShot ===")
    bootstrap_optimizer = dspy.BootstrapFewShot(
        metric=evaluation_accuracy,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )
    bootstrap_bot = bootstrap_optimizer.compile(
        InterviewBot(),
        trainset=trainset,
    )
    bootstrap_bot.save("models/bootstrap_fewshot.json")
    print("Saved: models/bootstrap_fewshot.json")

    # Phase 2: MIPROv2 optimization
    print("\n=== Phase 2: MIPROv2 ===")
    mipro_optimizer = dspy.MIPROv2(
        metric=evaluation_accuracy,
        auto="medium",
    )
    mipro_bot = mipro_optimizer.compile(
        InterviewBot(),
        trainset=trainset,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )
    mipro_bot.save("models/miprov2.json")
    print("Saved: models/miprov2.json")

    # Evaluate both on validation set
    print("\n=== Evaluation on validation set ===")
    for name, bot in [
        ("Uncompiled", InterviewBot()),
        ("BootstrapFewShot", bootstrap_bot),
        ("MIPROv2", mipro_bot),
    ]:
        correct = 0
        for ex in valset:
            pred = bot(**ex.inputs())
            if evaluation_accuracy(ex, pred):
                correct += 1
        acc = correct / len(valset) * 100
        print(f"{name}: {correct}/{len(valset)} = {acc:.0f}%")


if __name__ == "__main__":
    main()
