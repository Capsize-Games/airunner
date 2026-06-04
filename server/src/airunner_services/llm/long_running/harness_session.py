"""Single-session helpers for the long-running harness."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.llm.long_running.harness_session_checks import (
    project_error,
    project_status_result,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def run_session(
    agent: Any,
    project_id: int,
    feature_id: Optional[int] = None,
) -> dict[str, Any]:
    """Run a single working session on one project."""
    del feature_id
    logger.info("Running session for project %s", project_id)
    project = agent._project_manager.get_project(project_id)
    if project is None:
        return project_error(project_id)
    if (status_result := project_status_result(project)) is not None:
        return status_result
    result = agent._session_agent.run_session(project_id)
    if agent._on_progress:
        agent._on_progress({"event": "session_complete", "project_id": project_id, **result})
    return result


# The session facade only validates project state and forwards work to the
# dedicated session agent.
# Completion signaling stays here so callers see a single consistent event.