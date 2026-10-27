"""Session-end helpers for the long-running project manager."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from airunner_services.database.models.project_state import SessionState
from airunner_services.database.session import session_scope


def end_session(
    manager: Any,
    session_id: int,
    working_memory: Optional[dict[str, Any]] = None,
    next_action: Optional[str] = None,
    error: Optional[str] = None,
    tokens_consumed: int = 0,
) -> None:
    """End one working session."""
    with session_scope() as db:
        session = (
            db.query(SessionState)
            .filter(SessionState.id == session_id)
            .first()
        )
        if session is None:
            return
        session.ended_at = datetime.utcnow()
        session.working_memory = working_memory or {}
        session.next_recommended_action = next_action
        session.error_state = error
        session.tokens_consumed = tokens_consumed
        db.commit()
        manager._logger.info("Ended session %s", session_id)


def get_last_session(
    manager: Any,
    project_id: int,
) -> Optional[SessionState]:
    """Return the most recent session for one project."""
    with session_scope() as db:
        session = (
            db.query(SessionState)
            .filter(SessionState.project_id == project_id)
            .order_by(SessionState.started_at.desc())
            .first()
        )
        return manager._detach(db, session)


# Session-end helpers keep teardown writes and last-session lookup on one shared
# persistence surface.
# That makes resume flows reuse the same detached session representation.
# Token, memory, and error fields are finalized together when a session ends.
