import argparse
import dspy
import os
import sys
import mlflow
import uuid
from dotenv import load_dotenv
from mlflow.utils.git_utils import get_git_commit
from src.data import load_questions, flatten_questions
from src.orchestrator import InterviewOrchestrator
from src.modules import InterviewBot

VERSION = "0.3.2"
MAX_RETRIES = 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assessment Bot — interactive interview runner")
    parser.add_argument(
        "--questions",
        default="questions.json",
        help="Path to questions JSON file (default: questions.json)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model identifier (overrides MODEL from .env, e.g. openai/gpt-4o)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="OpenAI-compatible API base URL (overrides OPENAI_BASE_URL from .env)",
    )
    parser.add_argument(
        "--no-mlflow",
        action="store_true",
        help="Disable MLflow logging",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    # Setup
    if not args.no_mlflow:
        mlflow.set_experiment("Interview_Bot")
        git_commit = get_git_commit(".") or "local-dev"
        mlflow.set_active_model(name=f"assessment-bot-{git_commit[:8]}")
        mlflow.dspy.autolog()

    load_dotenv()

    # User and Session IDs
    user_id = input("Enter your Name/Candidate ID: ") or "anonymous"
    session_id = str(uuid.uuid4())

    # Ensure OPENAI_API_KEY is in environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Error: OPENAI_API_KEY not found. Set it in .env or environment.")

    base_url = args.base_url or os.getenv("OPENAI_BASE_URL")
    model = args.model or os.getenv("MODEL", "openai/qwen3.5:4b")

    lm_args = {"api_key": api_key}
    if base_url:
        lm_args["api_base"] = base_url  # litellm uses api_base for custom endpoints

    lm = dspy.LM(model, **lm_args)
    dspy.configure(lm=lm)

    data = load_questions(args.questions)
    all_questions = flatten_questions(data)

    orc = InterviewOrchestrator(all_questions)
    bot = InterviewBot()

    print(f"--- Starting Interview: {data['interview_id']} ---")

    try:
        while True:
            q = orc.get_current_question()
            if not q:
                break

            # Only print the full question if this is the first turn
            if orc.turns_in_question == 0:
                print(f"\n[{q['topic_name']}] Interviewer: {q['text']}")

            user_input = input("You: ")

            if args.no_mlflow:
                result = _call_bot_with_retry(bot, q, orc, user_input)
            else:
                with mlflow.start_span(name=f"{q['topic_name']}: {q['id']}") as span:
                    span.set_inputs({
                        "question": q["text"],
                        "user_input": user_input,
                        "attempt_number": orc.attempts,
                    })

                    result = _call_bot_with_retry(bot, q, orc, user_input)

                    span.set_outputs(result.action.model_dump())

                    mlflow.update_current_trace(
                        tags={"version": VERSION, "model": model},
                        metadata={
                            "mlflow.trace.user": user_id,
                            "mlflow.trace.session": session_id,
                        }
                    )

            action = result.action
            command = action.command

            # Orchestrator Override
            if orc.should_force_skip() and command == "GIVE_HINT":
                command = "PROMPT_SKIP"
                print("\n(System: Maximum attempts reached. Suggesting skip.)")

            print(f"\nInterviewer: {action.response}")

            orc.history.append(f"User: {user_input}")
            orc.history.append(f"Interviewer: {action.response}")
            orc.record_turn(command, action.evaluation)

        print("\n--- Interview Complete ---")
    except KeyboardInterrupt:
        print("\n--- Interview ended by user ---")


def _call_bot_with_retry(bot, q, orc, user_input):
    """Call the bot with retry logic for transient failures."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return bot(
                topic=q["topic_name"],
                question=q["text"],
                criteria=q["criteria"],
                hint_guidelines=q["hint_guidelines"],
                history=orc.history[-5:],
                user_input=user_input,
                attempt_number=orc.attempts,
                last_evaluation=orc.last_evaluation,
                next_topic=orc.get_next_topic_name(),
            )
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"\n(System: Retrying due to error: {e})")
                continue
            print(f"\n(System: LLM call failed after {MAX_RETRIES + 1} attempts: {e})")
            print("Please try answering again.")
            raise


if __name__ == "__main__":
    main()
