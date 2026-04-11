import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.orchestrator import InterviewOrchestrator

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)


def _safe_filename(user_id: str) -> str:
    """Sanitize user_id for use as a filename. Rejects path traversal."""
    if "/" in user_id or "\\" in user_id or ".." in user_id:
        raise ValueError(f"Invalid user_id: path traversal detected: {user_id!r}")
    return user_id


@dataclass
class SessionData:
    user_id: str
    interview_id: str
    orchestrator: InterviewOrchestrator
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


# Server-side registry: UUID -> SessionData
# Never sent to the browser. Holds sensitive data (criteria, hints, questions).
_registry: dict[str, SessionData] = {}

# Reverse index: user_id -> UUID (for resume lookup)
_user_index: dict[str, str] = {}


def create_session(user_id: str, questions: list[dict], interview_id: str) -> str:
    """Create a new interview session. Returns the session UUID."""
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
    if user_id in _user_index:
        return _user_index[user_id]

    path = SESSIONS_DIR / f"{_safe_filename(user_id)}.json"
    if not path.exists():
        return None

    try:
        with open(path) as f:
            saved = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt session file for user %s", user_id)
        return None

    session_uuid = saved["uuid"]
    orc = _deserialize_orchestrator(saved["orchestrator"], questions)
    if orc is None:
        return None

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
    path = SESSIONS_DIR / f"{_safe_filename(data.user_id)}.json"
    path.write_text(json.dumps(payload, indent=2))


def remove_session(uuid: str) -> None:
    """Remove session from registry and delete disk file."""
    data = _registry.pop(uuid, None)
    if data is None:
        return
    if data.user_id in _user_index:
        del _user_index[data.user_id]
    path = SESSIONS_DIR / f"{_safe_filename(data.user_id)}.json"
    if path.exists():
        path.unlink()


def _serialize_orchestrator(orc: InterviewOrchestrator) -> dict:
    """Serialize orchestrator state. Excludes question data."""
    return {
        "current_idx": orc.current_idx,
        "max_hints": orc.max_hints,
        "turns_in_question": orc.turns_in_question,
        "hints_given": orc.hints_given,
        "clarifications_requested": orc.clarifications_requested,
        "last_evaluation": orc.last_evaluation,
        "history": orc.history,
        "evaluation_history": orc.evaluation_history,
        "question_summaries": orc.question_summaries,
    }


def _deserialize_orchestrator(
    state: dict,
    questions: list[dict],
) -> Optional[InterviewOrchestrator]:
    """Rebuild orchestrator from saved state + fresh questions."""
    try:
        orc = InterviewOrchestrator(
            questions,
            max_hints=state.get("max_hints", state.get("max_attempts", 2)),
        )
        orc.current_idx = state["current_idx"]
        orc.turns_in_question = state["turns_in_question"]
        orc.hints_given = state.get("hints_given", state.get("attempts", 0))
        orc.clarifications_requested = state["clarifications_requested"]
        orc.last_evaluation = state["last_evaluation"]
        orc.history = state["history"]
        orc.evaluation_history = state["evaluation_history"]
        orc.question_summaries = state["question_summaries"]
        return orc
    except (KeyError, TypeError, IndexError):
        return None
