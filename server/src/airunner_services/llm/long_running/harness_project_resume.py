"""Resume-path helpers for harness project lifecycle operations."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import ProjectStatus
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def recovery_info(agent: Any, project_id: int) -> Optional[dict[str, Any]]:
    """Return recovery info from the last session when available."""
    last_session = agent._project_manager.get_last_session(project_id)
    if last_session is None:
        return None
    logger.info("Recovered context from session %s", last_session.id)
    return last_session.get_context_for_next_session()
    # Recovery only consults the latest session so resumption stays predictable.


def resume_project(agent: Any, project_id: int) -> dict[str, Any]:
    """Resume work on a paused or interrupted project."""
    logger.info("Resuming project %s", project_id)
    project = agent._project_manager.get_project(project_id)
    if project is None:
        return {"error": "Project not found"}
    resume_context = recovery_info(agent, project_id)
    if project.status == ProjectStatus.PAUSED:
        agent._project_manager.update_project_status(
            project_id, ProjectStatus.ACTIVE
        )
    result = agent.run_session(project_id)
    result["recovery_info"] = resume_context
    return result
    # Resume keeps state repair and the next session launch on the same path.
