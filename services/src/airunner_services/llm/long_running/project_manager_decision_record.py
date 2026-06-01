"""Decision-record helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import DecisionMemory
from airunner_services.database.session import session_scope
from airunner_services.utils.application.log_hygiene import summarize_text


def _decision_record(
    project_id: int,
    context: str,
    decision: str,
    reasoning: str,
    feature_id: Optional[int],
    tags: Optional[list[str]],
) -> DecisionMemory:
    """Build one decision-memory ORM record."""
    return DecisionMemory(
        project_id=project_id,
        feature_id=feature_id,
        decision_context=context,
        decision_made=decision,
        reasoning=reasoning,
        tags=tags or [],
    )


def record_decision(
    manager: Any, project_id: int, context: str, decision: str,
    reasoning: str, feature_id: Optional[int] = None,
    tags: Optional[list[str]] = None,
) -> DecisionMemory:
    """Record one decision for future reference."""
    with session_scope() as db:
        memory = _decision_record(
            project_id, context, decision, reasoning, feature_id, tags,
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        manager._logger.info(
            "Recorded decision (%s)",
            summarize_text(decision, label="decision"),
        )
        return manager._detach(db, memory)