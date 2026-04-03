import dspy
import os
import mlflow
from dotenv import load_dotenv
from src.data import load_questions
from src.orchestrator import InterviewOrchestrator
from src.modules import InterviewBot


def main():
    # Setup
    mlflow.set_experiment("Interview_Bot_v0.3.0")
    mlflow.dspy.autolog()
    load_dotenv()

    # Ensure OPENAI_API_KEY is in environment
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        print("Warning: OPENAI_API_KEY not found in environment.")

    lm_args = {"api_key": api_key}
    if base_url:
        lm_args["api_base"] = base_url  # litellm uses api_base for custom endpoints

    lm = dspy.LM("openai/qwen3.5:4b", **lm_args)
    dspy.configure(lm=lm)

    data = load_questions("questions.json")
    # Flatten questions for the orchestrator (POC simplification)
    all_questions = []
    for topic in data["topics"]:
        for q in topic["questions"]:
            q["topic_name"] = topic["topic_name"]
            all_questions.append(q)

    orc = InterviewOrchestrator(all_questions)
    bot = InterviewBot()

    print(f"--- Starting Interview: {data['interview_id']} ---")

    while True:
        q = orc.get_current_question()
        if not q:
            break

        # Only print the full question if this is the first turn
        if orc.turns_in_question == 0:
            print(f"\n[{q['topic_name']}] Interviewer: {q['text']}")

        user_input = input("You: ")
        # Call DSPy
        result = bot(
            topic=q["topic_name"],
            question=q["text"],
            criteria=q["criteria"],
            hint_guidelines=q["hint_guidelines"],
            history=orc.history[-5:],
            user_input=user_input,
            attempt_number=orc.attempts,
            last_evaluation=orc.last_evaluation,
            next_topic=orc.get_next_topic_name()
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


if __name__ == "__main__":
    main()
