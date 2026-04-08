import mlflow
import uuid
from mlflow.utils.git_utils import get_git_commit
from src.config import load_config, init_lm, load_interview_data
from src.orchestrator import InterviewOrchestrator
from src.modules import InterviewBot

VERSION = "0.3.2"
MAX_RETRIES = 2


def main():
    # Setup
    mlflow.set_experiment("Interview_Bot")

    git_commit = get_git_commit(".") or "local-dev"
    mlflow.set_active_model(name=f"assessment-bot-{git_commit[:8]}")

    mlflow.dspy.autolog()
    config = load_config()
    init_lm(config)

    # User and Session IDs
    user_id = input("Enter your Name/Candidate ID: ") or "anonymous"
    session_id = str(uuid.uuid4())

    data, all_questions = load_interview_data("questions.json")

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

            # Wrap bot call in MLflow span for trace metadata
            with mlflow.start_span(name=f"{q['topic_name']}: {q['id']}") as span:
                span.set_inputs(
                    {
                        "question": q["text"],
                        "user_input": user_input,
                        "attempt_number": orc.attempts,
                    }
                )

                result = _call_bot_with_retry(bot, q, orc, user_input)

                span.set_outputs(result.action.model_dump())

                # Update trace metadata - must be within span context
                mlflow.update_current_trace(
                    tags={"version": VERSION, "model": config["model"]},
                    metadata={
                        "mlflow.trace.user": user_id,
                        "mlflow.trace.session": session_id,
                    },
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
