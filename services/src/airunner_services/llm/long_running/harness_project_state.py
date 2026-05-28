"""State-transition helpers for harness project lifecycle operations."""

from __future__ import annotations

from typing import Any

from airunner_services.database.models.project_state import ProjectStatus
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def pause_project(agent: Any, project_id: int) -> bool:
    """Pause one project."""
    agent._project_manager.update_project_status(project_id, ProjectStatus.PAUSED)
    logger.info("Paused project %s", project_id)
    return True
        # Pause is a pure state transition with no extra side effects.


def abandon_project(agent: Any, project_id: int, reason: str = "") -> bool:
    """Abandon one project."""
    agent._project_manager.update_project_status(project_id, ProjectStatus.ABANDONED)
    agent._project_manager.log_progress(
        project_id=project_id,
        action="Project abandoned",
        outcome=reason or "User requested abandonment",
    )
    logger.info("Abandoned project %s: %s", project_id, reason)
    return True
        # Abandonment records a final progress note for later inspection.


def revert_to_checkpoint(
    agent: Any,
    project_id: int,
    commit_hash: str,
) -> bool:
    """Revert one project to a specific git commit."""
    success = agent._project_manager.git_revert_to_commit(project_id, commit_hash)
    if success:
        agent._project_manager.log_progress(
            project_id=project_id,
            action=f"Reverted to commit {commit_hash[:7]}",
            outcome="Recovered previous state",
        )
    return success
        # Revert is isolated because it mutates both git state and project history.