"""Decision-history helpers for the long-running harness."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import DecisionOutcome
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def get_decision_history(
    agent: Any,
    project_id: int,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get decision history for learning insights."""
    decisions = agent._project_manager.get_relevant_decisions(project_id, limit=limit)
    return [
        {
            "id": decision.id,
            "timestamp": str(decision.timestamp),
            "context": decision.decision_context,
            "decision": decision.decision_made,
            "reasoning": decision.reasoning,
            "outcome": decision.outcome.value if decision.outcome else None,
            "score": decision.outcome_score,
            "lesson": decision.lesson_learned,
        }
        for decision in decisions
    ]


def add_decision_feedback(
    agent: Any,
    decision_id: int,
    outcome: str,
    score: float,
    lesson: Optional[str] = None,
) -> None:
    """Add feedback for one past decision."""
    agent._project_manager.update_decision_outcome(
        decision_id=decision_id,
        outcome=DecisionOutcome(outcome),
        score=score,
        lesson=lesson,
    )
    logger.info("Added feedback for decision %s: %s", decision_id, outcome)