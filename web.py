import gradio as gr
import mlflow
from mlflow.utils.git_utils import get_git_commit

from src.config import init_lm, load_config, load_interview_data
from src.modules import InterviewBot
from src.session import (
    create_session,
    get_session,
    resume_session,
    save_session,
)

VERSION = "0.4.0"
MAX_RETRIES = 2

# --- Startup: load config, init LLM, load questions ---
config = load_config()
lm = init_lm(config)
interview_data, all_questions = load_interview_data()
bot = InterviewBot()

mlflow.set_experiment("Interview_Bot_Web")
git_commit = get_git_commit(".") or "local-dev"
mlflow.set_active_model(name=f"assessment-bot-web-{git_commit[:8]}")
mlflow.dspy.autolog()


# --- Helper functions ---


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
                continue
            raise RuntimeError(
                f"LLM call failed after {MAX_RETRIES + 1} attempts: {e}"
            ) from e


def _build_sidebar(orc):
    """Build display-safe sidebar content from orchestrator state."""
    q = orc.get_current_question()
    if q is None:
        return (
            "**Interview Complete**",
            "",
            "",
            "",
            _build_history(orc),
        )

    return (
        f"**Topic:** {q['topic_name']}",
        f"**Question:** {orc.current_idx + 1} / {len(orc.questions)}",
        f"**Attempts:** {orc.attempts} / {orc.max_attempts}",
        f"**Turn:** {orc.turns_in_question + 1}",
        _build_history(orc),
    )


def _build_history(orc):
    """Build evaluation history as display-safe markdown."""
    if not orc.question_summaries:
        return "_No questions answered yet_"

    lines = []
    badge_map = {
        "correct": "\u2713",
        "incorrect": "\u2717",
        "ambiguous": "~",
    }
    for summary in orc.question_summaries:
        qid = summary.get("question_id", "?")
        evaluation = summary.get("final_evaluation", "?")
        badge = badge_map.get(evaluation, "?")
        was_skipped = summary.get("was_force_skipped", False)
        label = f"{badge} {qid}"
        if was_skipped:
            label += " (skipped)"
        lines.append(label)

    # Current question
    q = orc.get_current_question()
    if q:
        lines.append(f"\u25cb {q['id']} (current)")

    return "\n".join(lines)


# --- Gradio App ---


def _build_ui():
    with gr.Blocks() as app:
        # --- Pre-interview state (user ID form) ---
        with gr.Column(visible=True) as login_group:
            gr.Markdown("## Assessment Bot")
            user_id_input = gr.Textbox(
                label="Enter your Name or Candidate ID",
                placeholder="e.g., john.doe",
            )
            start_btn = gr.Button("Start Interview", variant="primary")

        # --- Interview state (sidebar + chat) ---
        with gr.Column(visible=False) as interview_group:
            with gr.Sidebar():
                gr.Markdown("### Progress")
                sidebar_topic = gr.Markdown("**Topic:** -")
                sidebar_question = gr.Markdown("**Question:** -")
                sidebar_attempts = gr.Markdown("**Attempts:** 0 / 2")
                sidebar_turn = gr.Markdown("**Turn:** -")
                gr.Markdown("---")
                gr.Markdown("### History")
                sidebar_history = gr.Markdown("_No questions answered yet_")

            chatbot = gr.Chatbot(height=500)
            msg_input = gr.Textbox(
                placeholder="Type your answer...",
                show_label=False,
            )

        # State: display-safe only (session UUID + user ID)
        session_state = gr.State(None)

        # --- Event handlers ---

        def start_interview(user_id):
            """Handle user ID submission. Create or resume session."""
            if not user_id or not user_id.strip():
                gr.Warning("Please enter your name or candidate ID.")
                return (
                    gr.Column(visible=True),
                    gr.Column(visible=False),
                    None,
                    [],
                    "",
                    "",
                    "",
                    "",
                    "",
                )

            user_id = user_id.strip()

            # Try to resume existing session
            session_uuid = resume_session(user_id, all_questions)
            if session_uuid is None:
                session_uuid = create_session(
                    user_id, all_questions, interview_data["interview_id"]
                )

            data = get_session(session_uuid)
            orc = data.orchestrator

            # Build initial chat messages
            messages = []
            for entry in orc.history:
                role, _, text = entry.partition(": ")
                messages.append(
                    {
                        "role": "assistant" if role == "Interviewer" else "user",
                        "content": text,
                    }
                )

            # If no history, show first question
            q = orc.get_current_question()
            if not orc.history and q:
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"[{q['topic_name']}] {q['text']}",
                    }
                )

            sidebar = _build_sidebar(orc)

            return (
                gr.Column(visible=False),
                gr.Column(visible=True),
                {"session_uuid": session_uuid, "user_id": user_id},
                messages,
                *sidebar,
            )

        # Start interview on button click OR Enter key in the textbox
        gr.on(
            triggers=[start_btn.click, user_id_input.submit],
            fn=start_interview,
            inputs=[user_id_input],
            outputs=[
                login_group,
                interview_group,
                session_state,
                chatbot,
                sidebar_topic,
                sidebar_question,
                sidebar_attempts,
                sidebar_turn,
                sidebar_history,
            ],
            api_visibility="private",
        )

        def respond(message, history, state):
            """Handle candidate answer submission."""
            if state is None:
                return history, message, *[""] * 5

            session_uuid = state["session_uuid"]
            try:
                data = get_session(session_uuid)
            except KeyError:
                history.append(
                    {
                        "role": "assistant",
                        "content": "Session lost. Please refresh and re-enter your ID to resume.",
                    }
                )
                return history, "", *[""] * 5

            orc = data.orchestrator
            q = orc.get_current_question()

            if q is None:
                history.append(
                    {
                        "role": "assistant",
                        "content": "Interview is already complete.",
                    }
                )
                return history, "", *_build_sidebar(orc)

            # Add user message
            history.append({"role": "user", "content": message})

            # Call bot with retry
            try:
                with mlflow.start_span(name=f"{q['topic_name']}: {q['id']}") as span:
                    span.set_inputs(
                        {
                            "question": q["text"],
                            "user_input": message,
                            "attempt_number": orc.attempts,
                        }
                    )

                    result = _call_bot_with_retry(bot, q, orc, message)

                    span.set_outputs(result.action.model_dump())

                    mlflow.update_current_trace(
                        tags={"version": VERSION, "model": config["model"]},
                        metadata={
                            "mlflow.trace.user": data.user_id,
                            "mlflow.trace.session": session_uuid,
                        },
                    )
            except RuntimeError as e:
                history.append(
                    {
                        "role": "assistant",
                        "content": f"Error: {e}. Please try your answer again.",
                    }
                )
                return history, "", *_build_sidebar(orc)

            action = result.action
            command = action.command

            # Orchestrator override
            if orc.should_force_skip() and command == "GIVE_HINT":
                command = "PROMPT_SKIP"

            # Record turn
            orc.history.append(f"User: {message}")
            orc.history.append(f"Interviewer: {action.response}")
            orc.record_turn(command, action.evaluation)

            # Save session
            save_session(session_uuid)

            # Build response
            history.append({"role": "assistant", "content": action.response})

            # Check if interview complete
            next_q = orc.get_current_question()
            if next_q is None:
                summary_lines = ["---\n**Interview Complete!**\n"]
                for s in orc.question_summaries:
                    badge_map = {
                        "correct": "\u2713",
                        "incorrect": "\u2717",
                        "ambiguous": "~",
                    }
                    badge = badge_map.get(s["final_evaluation"], "?")
                    summary_lines.append(
                        f"{badge} {s['question_id']}: {s['final_evaluation']}"
                    )
                history.append(
                    {
                        "role": "assistant",
                        "content": "\n".join(summary_lines),
                    }
                )
            elif command in ("NEXT_QUESTION", "PROMPT_SKIP"):
                # Show next question
                history.append(
                    {
                        "role": "assistant",
                        "content": f"[{next_q['topic_name']}] {next_q['text']}",
                    }
                )

            sidebar = _build_sidebar(orc)
            return history, "", *sidebar

        msg_input.submit(
            respond,
            [msg_input, chatbot, session_state],
            [
                chatbot,
                msg_input,
                sidebar_topic,
                sidebar_question,
                sidebar_attempts,
                sidebar_turn,
                sidebar_history,
            ],
            api_visibility="private",
        )

    return app


app = _build_ui()

if __name__ == "__main__":
    app.launch(footer_links=["gradio", "settings"])
