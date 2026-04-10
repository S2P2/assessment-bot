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
    resume_session,
    save_session,
)
from web import _build_history, _build_sidebar, submit_answer


@pytest.fixture(autouse=True)
def _clear_registry():
    from src import session as session_mod

    session_mod._registry.clear()
    session_mod._user_index.clear()
    yield
    session_mod._registry.clear()
    session_mod._user_index.clear()


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
    assert "- \u2713 sql-1" in result
    assert "- \u25cb py-1" in result


def test_build_history_skipped():
    questions = _sample_questions()
    orc = InterviewOrchestrator(questions, max_attempts=2)
    orc.record_turn("GIVE_HINT", "incorrect")
    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.should_force_skip()
    orc.record_turn("PROMPT_SKIP", "incorrect")
    result = _build_history(orc)
    assert "skipped" in result
    assert result.startswith("-")


def test_session_state_no_sensitive_data():
    """Verify gr.State() would only contain display-safe data."""
    questions = _sample_questions()
    uuid = create_session("testuser", questions, "test-interview")

    # Simulate what goes into gr.State -- only uuid + user_id
    client_state = {"session_uuid": uuid, "user_id": "testuser"}

    # Verify no sensitive data leaks
    assert "criteria" not in str(client_state)
    assert "hint_guidelines" not in str(client_state)

    # Verify sensitive data IS in server-side registry
    server_data = get_session(uuid)
    assert server_data.orchestrator is not None
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
    with open(tmp_path / "user1.json") as f:
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
    session_mod._user_index.clear()

    resumed_uuid = resume_session("user1", questions)
    assert resumed_uuid == uuid

    resumed = get_session(resumed_uuid)
    assert "User: my answer" in resumed.orchestrator.history
    assert "Interviewer: Good response" in resumed.orchestrator.history
    assert resumed.orchestrator.attempts == 1


def test_submit_answer_empty_message():
    """Empty messages are rejected — no bubble added."""
    history = []
    result_history, result_msg = submit_answer(
        "", history, {"session_uuid": "abc", "user_id": "u1"}
    )
    assert result_history == []
    assert result_msg == ""


def test_submit_answer_whitespace_message():
    """Whitespace-only messages are rejected."""
    history = []
    result_history, result_msg = submit_answer(
        "   ", history, {"session_uuid": "abc", "user_id": "u1"}
    )
    assert result_history == []
    assert result_msg == ""


def test_submit_answer_appends_user_message():
    """Valid message appends to history and clears input."""
    history = []
    result_history, result_msg = submit_answer(
        "SELECT * FROM users", history, {"session_uuid": "abc", "user_id": "u1"}
    )
    assert len(result_history) == 1
    assert result_history[0]["role"] == "user"
    assert result_history[0]["content"] == "SELECT * FROM users"
    assert result_msg == ""


def test_submit_answer_no_state():
    """No session state returns unchanged history."""
    history = []
    result_history, result_msg = submit_answer("hello", history, None)
    assert result_history == []
    assert result_msg == ""
