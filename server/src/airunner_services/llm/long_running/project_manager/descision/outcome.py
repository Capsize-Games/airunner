"""Decision-outcome helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import (
    DecisionMemory,
    DecisionOutcome,
)
from airunner_services.database.session import session_scope


def update_decision_outcome(
    manager: Any,
    decision_id: int,
    outcome: DecisionOutcome,
    score: float,
    lesson: Optional[str] = None,
) -> None:
    """Update one decision with its outcome."""
    del manager
    with session_scope() as db:
        memory = (
            db.query(DecisionMemory)
            .filter(DecisionMemory.id == decision_id)
            .first()
        )
        if memory is None:
            return
        memory.outcome = outcome
        memory.outcome_score = max(-1.0, min(1.0, score))
        memory.lesson_learned = lesson
        db.commit()


# Decision outcome updates stay isolated so project-manager orchestration can
# reuse the same persistence path.
# Score clamping happens here to keep outcome writes consistent.
