"""Autonomous session-loop helpers for the long-running harness."""

from __future__ import annotations

from typing import Any

from airunner_services.llm.long_running.harness_autonomous_iteration import (
    project_iteration_result,
    run_iteration,
)
from airunner_services.llm.long_running.harness_autonomous_results import (
    incomplete_result,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def run_until_complete(
    agent: Any,
    project_id: int,
    max_sessions: int = 100,
    pause_between_sessions: bool = False,
) -> dict[str, Any]:
    """Run sessions until one project completes or the cap is reached."""
    logger.info(
        "Running until complete: project %s, max %s", project_id, max_sessions
    )
    sessions_run = 0
    errors: list[str] = []
    for _ in range(max_sessions):
        project, terminal = project_iteration_result(
            agent, project_id, sessions_run
        )
        if terminal is not None:
            return terminal
        sessions_run += 1
        terminal = run_iteration(
            agent,
            project_id,
            sessions_run,
            max_sessions,
            project,
            errors,
            pause_between_sessions,
        )
        if terminal is not None:
            return terminal
    return incomplete_result(
        agent._project_manager.get_project(project_id),
        max_sessions,
        sessions_run,
    )


# The outer loop stays responsible only for project-level termination and
# session counting.
# Per-iteration state transitions live in the neighboring iteration helper.
