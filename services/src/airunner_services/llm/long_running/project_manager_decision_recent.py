"""Decision-query helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import DecisionMemory
from airunner_services.database.session import session_scope


def get_relevant_decisions(
    manager: Any,
    project_id: int,
    tags: Optional[list[str]] = None,
    limit: int = 10,
) -> list[DecisionMemory]:
    """Return recent decisions for one project."""
    del tags
    with session_scope() as db:
        decisions = (
            db.query(DecisionMemory)
            .filter(DecisionMemory.project_id == project_id)
            .order_by(DecisionMemory.timestamp.desc())
            .limit(limit)
            .all()
        )
        return manager._detach_all(db, decisions)