# Gradio 6 Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a candidate-facing Gradio 6 web UI for the assessment bot with session persistence and server-side security.

**Architecture:** Thin wrapper — `web.py` imports existing orchestrator/bot directly. Shared setup extracted to `src/config.py`. Session persistence via `src/session.py` with JSON files. Sensitive data (criteria, hints) kept in server-side registry, never sent to browser via `gr.State()`.

**Tech Stack:** Python 3.13, Gradio 6, DSPy, Pydantic, uv

**Spec:** `docs/superpowers/specs/2026-04-08-gradio-web-ui-design.md`

**Branch:** `feat/gradio-ui` (from `main`)

---

### Task 1: Create feature branch and add Gradio dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

- [ ] **Step 1: Create feature branch from main**

```bash
git checkout main
git checkout -b feat/gradio-ui
```

- [ ] **Step 2: Add gradio to dependencies in pyproject.toml**

Add `"gradio>=6.0"` to the `dependencies` list in `pyproject.toml`:

```toml
dependencies = [
    "dspy>=3.1.3",
    "gradio>=6.0",
    "jsonschema>=4.23.0",
    "mlflow>=3.10.1",
    "openai>=2.30.0",
    "pydantic>=2.12.5",
    "pytest>=9.0.2",
    "python-dotenv>=1.2.2",
]
```

- [ ] **Step 3: Add sessions/ to .gitignore**

Append to `.gitignore`:

```
# Session data
sessions/
```

- [ ] **Step 4: Install dependencies**

```bash
uv sync
```

- [ ] **Step 5: Verify gradio imports**

```bash
uv run python -c "import gradio; print(gradio.__version__)"
```

Expected: version 6.x.x

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore uv.lock
git commit -m "chore: add gradio>=6.0 dependency and gitignore sessions/"
```

---

### Task 2: Extract shared config into `src/config.py`

**Files:**
- Create: `src/config.py`
- Modify: `main.py`
- Create: `tests/test_config.py`

This task extracts duplicated setup logic from `main.py` into a shared module. The web app and CLI both use it.

- [ ] **Step 1: Write failing tests for `src/config.py`**

Create `tests/test_config.py`:

```python
import os
import pytest
from unittest.mock import patch
from src.config import load_config, init_lm, load_interview_data


def test_load_config_reads_env():
    env = {
        "OPENAI_API_KEY": "test-key-123",
        "MODEL": "openai/gpt-test",
        "OPENAI_BASE_URL": "http://localhost:8080",
    }
    with patch.dict(os.environ, env, clear=False):
        config = load_config()
    assert config["api_key"] == "test-key-123"
    assert config["model"] == "openai/gpt-test"
    assert config["base_url"] == "http://localhost:8080"


def test_load_config_defaults_model():
    env = {"OPENAI_API_KEY": "test-key-123"}
    with patch.dict(os.environ, env, clear=False):
        # Remove MODEL if set
        os.environ.pop("MODEL", None)
        config = load_config()
    assert config["model"] == "openai/qwen3.5:4b"


def test_load_config_missing_api_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
            load_config()


def test_load_interview_data_returns_tuple():
    data, questions = load_interview_data("questions.json")
    assert data["interview_id"] == "it-skill-eval-v1"
    assert len(questions) == 3
    assert all("id" in q for q in questions)
    assert all("topic_name" in q for q in questions)


def test_load_interview_data_invalid_path():
    with pytest.raises(SystemExit):
        load_interview_data("nonexistent.json")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Implement `src/config.py`**

Create `src/config.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Refactor `main.py` to use `src/config.py`**

Replace the duplicated setup in `main.py`. The refactored `main.py`:

```python
import uuid

import mlflow
from mlflow.utils.git_utils import get_git_commit

from src.config import init_lm, load_config, load_interview_data
from src.modules import InterviewBot
from src.orchestrator import InterviewOrchestrator

VERSION = "0.3.2"
MAX_RETRIES = 2


def main():
    config = load_config()
    lm = init_lm(config)

    mlflow.set_experiment("Interview_Bot")
    git_commit = get_git_commit(".") or "local-dev"
    mlflow.set_active_model(name=f"assessment-bot-{git_commit[:8]}")
    mlflow.dspy.autolog()

    data, all_questions = load_interview_data()

    user_id = input("Enter your Name/Candidate ID: ") or "anonymous"
    session_id = str(uuid.uuid4())

    orc = InterviewOrchestrator(all_questions)
    bot = InterviewBot()

    print(f"--- Starting Interview: {data['interview_id']} ---")

    try:
        while True:
            q = orc.get_current_question()
            if not q:
                break

            if orc.turns_in_question == 0:
                print(f"\n[{q['topic_name']}] Interviewer: {q['text']}")

            user_input = input("You: ")

            with mlflow.start_span(name=f"{q['topic_name']}: {q['id']}") as span:
                span.set_inputs({
                    "question": q["text"],
                    "user_input": user_input,
                    "attempt_number": orc.attempts,
                })

                result = _call_bot_with_retry(bot, q, orc, user_input)

                span.set_outputs(result.action.model_dump())

                mlflow.update_current_trace(
                    tags={"version": VERSION, "model": config["model"]},
                    metadata={
                        "mlflow.trace.user": user_id,
                        "mlflow.trace.session": session_id,
                    },
                )

            action = result.action
            command = action.command

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
            print(
                f"\n(System: LLM call failed after {MAX_RETRIES + 1} attempts: {e})"
            )
            print("Please try answering again.")
            raise


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run existing tests to verify no regressions**

```bash
uv run pytest tests/ -v
```

Expected: all existing tests PASS

- [ ] **Step 7: Run linter**

```bash
uv run ruff check src/config.py main.py tests/test_config.py
```

Expected: no issues

- [ ] **Step 8: Commit**

```bash
git add src/config.py main.py tests/test_config.py
git commit -m "feat: extract shared config from main.py into src/config.py"
```

---

### Task 3: Implement session persistence (`src/session.py`)

**Files:**
- Create: `src/session.py`
- Create: `tests/test_session.py`

This task creates the session persistence layer: JSON file storage, server-side registry, and serialization.

- [ ] **Step 1: Write failing tests for `src/session.py`**

Create `tests/test_session.py`:

```python
import json
from datetime import datetime

import pytest

from src.orchestrator import InterviewOrchestrator
from src.session import (
    SessionData,
    create_session,
    get_session,
    remove_session,
    resume_session,
    save_session,
)


@pytest.fixture(autouse=True)
def _clear_registry():
    """Clear the session registry between tests."""
    from src import session as session_mod

    session_mod._registry.clear()
    yield
    session_mod._registry.clear()


def _sample_questions():
    return [
        {"id": "sql-1", "text": "Q1", "criteria": "c1", "hint_guidelines": "h1", "topic_name": "SQL"},
        {"id": "py-1", "text": "Q2", "criteria": "c2", "hint_guidelines": "h2", "topic_name": "Python"},
    ]


def test_create_session_returns_uuid():
    uuid = create_session("user1", _sample_questions(), "test-interview")
    assert isinstance(uuid, str)
    assert len(uuid) == 36  # standard UUID format


def test_create_session_populates_registry():
    uuid = create_session("user1", _sample_questions(), "test-interview")
    data = get_session(uuid)
    assert isinstance(data, SessionData)
    assert data.user_id == "user1"
    assert data.interview_id == "test-interview"
    assert isinstance(data.orchestrator, InterviewOrchestrator)
    assert data.orchestrator.current_idx == 0


def test_get_session_missing_raises():
    with pytest.raises(KeyError):
        get_session("nonexistent-uuid")


def test_save_and_resume_session(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    questions = _sample_questions()
    uuid = create_session("user1", questions, "test-interview")

    # Simulate some interview progress
    data = get_session(uuid)
    data.orchestrator.record_turn("NEXT_QUESTION", "correct")
    save_session(uuid)

    # Clear registry to simulate server restart
    from src import session as session_mod
    session_mod._registry.clear()

    # Resume should reload from disk
    resumed_uuid = resume_session("user1", questions)
    assert resumed_uuid == uuid

    resumed_data = get_session(resumed_uuid)
    assert resumed_data.orchestrator.current_idx == 1
    assert resumed_data.orchestrator.question_summaries[0]["final_evaluation"] == "correct"


def test_resume_session_no_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    result = resume_session("nobody", _sample_questions())
    assert result is None


def test_remove_session(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    uuid = create_session("user1", _sample_questions(), "test-interview")
    save_session(uuid)

    # Verify file exists
    assert (tmp_path / f"{uuid}.json").exists()

    remove_session(uuid)

    # Registry entry gone
    with pytest.raises(KeyError):
        get_session(uuid)

    # File gone
    assert not (tmp_path / f"{uuid}.json").exists()


def test_session_file_has_no_sensitive_data(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    questions = _sample_questions()
    uuid = create_session("user1", questions, "test-interview")
    save_session(uuid)

    with open(tmp_path / f"{uuid}.json") as f:
        saved = json.load(f)

    # Must NOT contain criteria or hint_guidelines
    assert "questions" not in saved
    orc_data = saved["orchestrator"]
    assert "criteria" not in str(orc_data)
    assert "hint_guidelines" not in str(orc_data)


def test_session_file_format(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    uuid = create_session("user1", _sample_questions(), "test-interview")
    save_session(uuid)

    with open(tmp_path / f"{uuid}.json") as f:
        saved = json.load(f)

    assert saved["uuid"] == uuid
    assert saved["user_id"] == "user1"
    assert saved["interview_id"] == "test-interview"
    assert "created_at" in saved
    assert "updated_at" in saved
    assert isinstance(saved["orchestrator"], dict)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_session.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.session'`

- [ ] **Step 3: Implement `src/session.py`**

Create `src/session.py`:

```python
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.orchestrator import InterviewOrchestrator

SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)


@dataclass
class SessionData:
    user_id: str
    interview_id: str
    orchestrator: InterviewOrchestrator
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# Server-side registry: UUID -> SessionData
# Never sent to the browser. Holds sensitive data (criteria, hints, questions).
_registry: dict[str, SessionData] = {}

# Reverse index: user_id -> UUID (for resume lookup)
_user_index: dict[str, str] = {}


def create_session(user_id: str, questions: list[dict], interview_id: str) -> str:
    """Create a new interview session. Returns the session UUID."""
    import uuid

    session_uuid = str(uuid.uuid4())
    orc = InterviewOrchestrator(questions)
    data = SessionData(
        user_id=user_id,
        interview_id=interview_id,
        orchestrator=orc,
    )
    _registry[session_uuid] = data
    _user_index[user_id] = session_uuid
    save_session(session_uuid)
    return session_uuid


def resume_session(user_id: str, questions: list[dict]) -> Optional[str]:
    """Resume an existing session from disk. Returns UUID or None."""
    # Check if already in memory
    if user_id in _user_index:
        return _user_index[user_id]

    # Scan sessions dir for this user
    if not SESSIONS_DIR.exists():
        return None

    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(path) as f:
                saved = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if saved.get("user_id") != user_id:
            continue

        session_uuid = saved["uuid"]
        orc = _deserialize_orchestrator(saved["orchestrator"], questions)
        if orc is None:
            continue

        data = SessionData(
            user_id=user_id,
            interview_id=saved["interview_id"],
            orchestrator=orc,
            created_at=saved["created_at"],
            updated_at=saved["updated_at"],
        )
        _registry[session_uuid] = data
        _user_index[user_id] = session_uuid
        return session_uuid

    return None


def get_session(uuid: str) -> SessionData:
    """Look up session from the server-side registry."""
    if uuid not in _registry:
        raise KeyError(f"Session not found: {uuid}")
    return _registry[uuid]


def save_session(uuid: str) -> None:
    """Persist session state to disk."""
    data = _registry[uuid]
    data.updated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "uuid": uuid,
        "user_id": data.user_id,
        "interview_id": data.interview_id,
        "created_at": data.created_at,
        "updated_at": data.updated_at,
        "orchestrator": _serialize_orchestrator(data.orchestrator),
    }
    path = SESSIONS_DIR / f"{uuid}.json"
    path.write_text(json.dumps(payload, indent=2))


def remove_session(uuid: str) -> None:
    """Remove session from registry and delete disk file."""
    data = _registry.pop(uuid, None)
    if data and data.user_id in _user_index:
        del _user_index[data.user_id]
    path = SESSIONS_DIR / f"{uuid}.json"
    if path.exists():
        path.unlink()


def _serialize_orchestrator(orc: InterviewOrchestrator) -> dict:
    """Serialize orchestrator state. Excludes question data."""
    return {
        "current_idx": orc.current_idx,
        "attempts": orc.attempts,
        "max_attempts": orc.max_attempts,
        "turns_in_question": orc.turns_in_question,
        "hints_given": orc.hints_given,
        "clarifications_requested": orc.clarifications_requested,
        "last_evaluation": orc.last_evaluation,
        "history": orc.history,
        "evaluation_history": orc.evaluation_history,
        "question_summaries": orc.question_summaries,
    }


def _deserialize_orchestrator(
    state: dict, questions: list[dict]
) -> Optional[InterviewOrchestrator]:
    """Rebuild orchestrator from saved state + fresh questions."""
    try:
        orc = InterviewOrchestrator(questions, max_attempts=state.get("max_attempts", 2))
        orc.current_idx = state["current_idx"]
        orc.attempts = state["attempts"]
        orc.turns_in_question = state["turns_in_question"]
        orc.hints_given = state["hints_given"]
        orc.clarifications_requested = state["clarifications_requested"]
        orc.last_evaluation = state["last_evaluation"]
        orc.history = state["history"]
        orc.evaluation_history = state["evaluation_history"]
        orc.question_summaries = state["question_summaries"]
        return orc
    except (KeyError, TypeError, IndexError):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_session.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Run linter**

```bash
uv run ruff check src/session.py tests/test_session.py
```

Expected: no issues

- [ ] **Step 6: Commit**

```bash
git add src/session.py tests/test_session.py
git commit -m "feat: add session persistence with server-side registry"
```

---

### Task 4: Build the Gradio web UI (`web.py`)

**Files:**
- Create: `web.py`

This is the main Gradio app. It uses `src/config.py` for setup and `src/session.py` for session management.

- [ ] **Step 1: Create `web.py`**

```python
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

            chatbot = gr.Chatbot(type="messages", height=500)
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
                messages.append({
                    "role": "assistant" if role == "Interviewer" else "user",
                    "content": text,
                })

            # If no history, show first question
            q = orc.get_current_question()
            if not orc.history and q:
                messages.append({
                    "role": "assistant",
                    "content": f"[{q['topic_name']}] {q['text']}",
                })

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
                history.append({
                    "role": "assistant",
                    "content": "Session lost. Please refresh and re-enter your ID to resume.",
                })
                return history, "", *[""] * 5

            orc = data.orchestrator
            q = orc.get_current_question()

            if q is None:
                history.append({
                    "role": "assistant",
                    "content": "Interview is already complete.",
                })
                return history, "", *_build_sidebar(orc)

            # Add user message
            history.append({"role": "user", "content": message})

            # Call bot with retry
            try:
                with mlflow.start_span(name=f"{q['topic_name']}: {q['id']}") as span:
                    span.set_inputs({
                        "question": q["text"],
                        "user_input": message,
                        "attempt_number": orc.attempts,
                    })

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
                history.append({
                    "role": "assistant",
                    "content": f"Error: {e}. Please try your answer again.",
                })
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
                    badge_map = {"correct": "\u2713", "incorrect": "\u2717", "ambiguous": "~"}
                    badge = badge_map.get(s["final_evaluation"], "?")
                    summary_lines.append(
                        f"{badge} {s['question_id']}: {s['final_evaluation']}"
                    )
                history.append({
                    "role": "assistant",
                    "content": "\n".join(summary_lines),
                })
            elif command in ("NEXT_QUESTION", "PROMPT_SKIP"):
                # Show next question
                history.append({
                    "role": "assistant",
                    "content": f"[{next_q['topic_name']}] {next_q['text']}",
                })

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
```

- [ ] **Step 2: Verify the app starts**

```bash
uv run python -c "from web import app; print('App loaded successfully')"
```

Expected: `App loaded successfully` (requires valid `.env` with `OPENAI_API_KEY`)

- [ ] **Step 3: Run linter**

```bash
uv run ruff check web.py
```

Fix any issues.

- [ ] **Step 4: Commit**

```bash
git add web.py
git commit -m "feat: add Gradio 6 web UI with sidebar and session management"
```

---

### Task 5: Write integration tests for the web UI

**Files:**
- Create: `tests/test_web.py`

Integration tests that verify the web UI logic without starting a real Gradio server.

- [ ] **Step 1: Write integration tests**

Create `tests/test_web.py`:

```python
"""Integration tests for web.py turn handler logic.

Tests the core logic (session management, orchestrator interaction,
sidebar building) without launching a real Gradio server.
"""

import json

import pytest

from src.orchestrator import InterviewOrchestrator
from src.session import (
    SessionData,
    create_session,
    get_session,
    remove_session,
    resume_session,
    save_session,
)
from web import _build_sidebar, _build_history


@pytest.fixture(autouse=True)
def _clear_registry():
    from src import session as session_mod

    session_mod._registry.clear()
    yield
    session_mod._registry.clear()


def _sample_questions():
    return [
        {
            "id": "sql-1",
            "text": "What is SELECT?",
            "criteria": "must explain SELECT",
            "hint_guidelines": "nudge toward querying",
            "topic_name": "SQL",
        },
        {
            "id": "py-1",
            "text": "What is a list?",
            "criteria": "must explain lists",
            "hint_guidelines": "nudge toward collections",
            "topic_name": "Python",
        },
    ]


def test_build_sidebar_active_question():
    questions = _sample_questions()
    orc = InterviewOrchestrator(questions)
    topic, question, attempts, turn, history = _build_sidebar(orc)

    assert "SQL" in topic
    assert "1 / 2" in question
    assert "0 / 2" in attempts


def test_build_sidebar_complete():
    questions = _sample_questions()
    orc = InterviewOrchestrator(questions)
    orc.record_turn("NEXT_QUESTION", "correct")
    orc.record_turn("NEXT_QUESTION", "correct")
    topic, question, attempts, turn, history = _build_sidebar(orc)

    assert "Complete" in topic


def test_build_history_empty():
    orc = InterviewOrchestrator(_sample_questions())
    result = _build_history(orc)
    assert "No questions" in result


def test_build_history_with_summaries():
    questions = _sample_questions()
    orc = InterviewOrchestrator(questions)
    orc.record_turn("NEXT_QUESTION", "correct")
    result = _build_history(orc)
    assert "\u2713 sql-1" in result
    assert "sql-2" in result or "py-1" in result  # next question shown


def test_build_history_skipped():
    questions = _sample_questions()
    orc = InterviewOrchestrator(questions, max_attempts=2)
    orc.record_turn("GIVE_HINT", "incorrect")
    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.should_force_skip()
    orc.record_turn("PROMPT_SKIP", "incorrect")
    result = _build_history(orc)
    assert "skipped" in result


def test_session_state_no_sensitive_data():
    """Verify gr.State() would only contain display-safe data."""
    questions = _sample_questions()
    uuid = create_session("testuser", questions, "test-interview")

    # Simulate what goes into gr.State — only uuid + user_id
    client_state = {"session_uuid": uuid, "user_id": "testuser"}

    # Verify no sensitive data leaks
    assert "criteria" not in str(client_state)
    assert "hint_guidelines" not in str(client_state)

    # Verify sensitive data IS in server-side registry
    server_data = get_session(uuid)
    assert server_data.orchestrator is not None
    # The questions list is accessible server-side but not from client_state
    assert isinstance(server_data, SessionData)


def test_full_interview_lifecycle(tmp_path, monkeypatch):
    """Test complete session: create, progress, save, resume."""
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    questions = _sample_questions()
    uuid = create_session("user1", questions, "test-interview")

    # Simulate interview turns
    data = get_session(uuid)
    orc = data.orchestrator
    q = orc.get_current_question()
    assert q["id"] == "sql-1"

    orc.history.append("User: SELECT gets data")
    orc.history.append("Interviewer: Correct!")
    orc.record_turn("NEXT_QUESTION", "correct")
    save_session(uuid)

    # Verify progress
    data = get_session(uuid)
    assert data.orchestrator.current_idx == 1
    assert len(data.orchestrator.question_summaries) == 1

    # Complete interview
    orc = data.orchestrator
    orc.history.append("User: A list holds items")
    orc.history.append("Interviewer: Correct!")
    orc.record_turn("NEXT_QUESTION", "correct")
    save_session(uuid)

    assert orc.get_current_question() is None

    # Verify session file
    with open(tmp_path / f"{uuid}.json") as f:
        saved = json.load(f)
    assert saved["orchestrator"]["current_idx"] == 2
    assert len(saved["orchestrator"]["question_summaries"]) == 2


def test_resume_preserves_history(tmp_path, monkeypatch):
    """Verify chat history survives a resume."""
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    questions = _sample_questions()
    uuid = create_session("user1", questions, "test-interview")

    data = get_session(uuid)
    data.orchestrator.history.append("User: my answer")
    data.orchestrator.history.append("Interviewer: Good response")
    data.orchestrator.record_turn("GIVE_HINT", "incorrect")
    save_session(uuid)

    # Clear and resume
    from src import session as session_mod
    session_mod._registry.clear()

    resumed_uuid = resume_session("user1", questions)
    assert resumed_uuid == uuid

    resumed = get_session(resumed_uuid)
    assert "User: my answer" in resumed.orchestrator.history
    assert "Interviewer: Good response" in resumed.orchestrator.history
    assert resumed.orchestrator.attempts == 1
```

- [ ] **Step 2: Run the tests**

```bash
uv run pytest tests/test_web.py -v
```

Expected: all tests PASS

- [ ] **Step 3: Run the full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASS (including existing tests)

- [ ] **Step 4: Run linter on everything**

```bash
uv run ruff check src/ tests/ web.py main.py
uv run ruff format --check src/ tests/ web.py main.py
```

Expected: no issues

- [ ] **Step 5: Commit**

```bash
git add tests/test_web.py
git commit -m "test: add integration tests for Gradio web UI"
```

---

### Task 6: Update project metadata and final verification

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update version in pyproject.toml**

Bump version to reflect the new web UI feature:

```toml
version = "0.4.0"
```

Also update the description:

```toml
description = "IT skill interview bot powered by DSPy with CLI and web UI"
```

- [ ] **Step 2: Update version in `web.py` if needed**

The `VERSION` in `web.py` should match. It's already `"0.4.0"` from Task 4.

- [ ] **Step 3: Run the full test suite one final time**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 4: Run full lint check**

```bash
uv run ruff check src/ tests/ web.py main.py
uv run ruff format --check src/ tests/ web.py main.py
```

Expected: clean

- [ ] **Step 5: Verify web app can be imported**

```bash
uv run python -c "from web import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.4.0 for Gradio web UI"
```
