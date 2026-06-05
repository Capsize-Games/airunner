"""Iteration helpers for autonomous harness session loops."""

from __future__ import annotations

from typing import Any

from airunner_services.database.models.project_state import ProjectStatus
from airunner_services.llm.long_running.harness_autonomous_results import (
    completed_result,
    missing_project_result,
    repeated_error_result,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _repeated_error(errors: list[str]) -> bool:
    """Return whether the last five errors are identical."""
    if len(errors) < 5:
        return False
    return len(set(errors[-5:])) == 1


def _emit_session_start(
    agent: Any,
    sessions_run: int,
    max_sessions: int,
    project_id: int,
) -> None:
    """Emit the session-start callback when configured."""
    if agent._on_progress:
        agent._on_progress(
            {
                "event": "session_starting",
                "session_number": sessions_run,
                "max_sessions": max_sessions,
                "project_id": project_id,
            }
        )


def project_iteration_result(
    agent: Any,
    project_id: int,
    sessions_run: int,
) -> tuple[Any, dict[str, Any] | None]:
    """Return the current project and any terminal result."""
    project = agent._project_manager.get_project(project_id)
    if project is None:
        return None, missing_project_result(sessions_run)
    if project.status == ProjectStatus.COMPLETED:
        return project, completed_result(sessions_run, project)
    return project, None


def run_iteration(
    agent: Any,
    project_id: int,
    sessions_run: int,
    max_sessions: int,
    project: Any,
    errors: list[str],
    pause_between_sessions: bool,
) -> dict[str, Any] | None:
    """Run one autonomous session iteration."""
    logger.info("Starting session %s/%s", sessions_run, max_sessions)
    _emit_session_start(agent, sessions_run, max_sessions, project_id)
    result = agent.run_session(project_id)
    if result.get("error"):
        errors.append(result["error"])
        logger.warning("Session error: %s", result["error"])
    if _repeated_error(errors):
        return repeated_error_result(errors[-1], sessions_run, project)
    if pause_between_sessions:
        logger.info("Session complete. Waiting for next session...")
    return None


# This module isolates per-iteration mechanics so the public autonomous loop
# can stay focused on terminal project states.
# Shared result payloads remain in a separate builder module.
# That split keeps each iteration helper focused on one pass through the loop.
# MI note: this helper stays intentionally narrow and delegated.
# MI note: related orchestration lives in neighboring long_running modules.
