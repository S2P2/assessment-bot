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


@pytest.fixture(autouse=True)
def _clear_registry():
    """Clear the session registry between tests."""
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
            "text": "Q1",
            "criteria": "c1",
            "hint_guidelines": "h1",
            "topic_name": "SQL",
        },
        {
            "id": "py-1",
            "text": "Q2",
            "criteria": "c2",
            "hint_guidelines": "h2",
            "topic_name": "Python",
        },
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
    session_mod._user_index.clear()

    # Resume should reload from disk
    resumed_uuid = resume_session("user1", questions)
    assert resumed_uuid == uuid

    resumed_data = get_session(resumed_uuid)
    assert resumed_data.orchestrator.current_idx == 1
    assert (
        resumed_data.orchestrator.question_summaries[0]["final_evaluation"] == "correct"
    )


def test_resume_session_no_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    result = resume_session("nobody", _sample_questions())
    assert result is None


def test_remove_session(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    uuid = create_session("user1", _sample_questions(), "test-interview")
    save_session(uuid)

    # Verify file exists
    assert (tmp_path / "user1.json").exists()

    remove_session(uuid)

    # Registry entry gone
    with pytest.raises(KeyError):
        get_session(uuid)

    # File gone
    assert not (tmp_path / "user1.json").exists()


def test_session_file_has_no_sensitive_data(tmp_path, monkeypatch):
    monkeypatch.setattr("src.session.SESSIONS_DIR", tmp_path)

    questions = _sample_questions()
    uuid = create_session("user1", questions, "test-interview")
    save_session(uuid)

    with open(tmp_path / "user1.json") as f:
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

    with open(tmp_path / "user1.json") as f:
        saved = json.load(f)

    assert saved["uuid"] == uuid
    assert saved["user_id"] == "user1"
    assert saved["interview_id"] == "test-interview"
    assert "created_at" in saved
    assert "updated_at" in saved
    assert isinstance(saved["orchestrator"], dict)
