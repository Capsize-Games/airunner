"""Run helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.llm.long_running.session_agent_state import (
    SessionPhase,
    SessionWorkflowState,
)


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _initial_state(project_id: int) -> SessionWorkflowState:
    """Build the initial state for one session run."""
    return {
        "messages": [],
        "project_id": project_id,
        "session_id": None,
        "feature_id": None,
        "phase": SessionPhase.ORIENTATION,
        "progress_context": "",
        "git_context": "",
        "feature_context": "",
        "decision_context": "",
        "tools_output": None,
        "verification_result": None,
        "files_changed": [],
        "error": None,
        "should_continue": True,
    }


def run_session(
    agent: Any,
    project_id: int,
    max_iterations: int = 10,
) -> dict[str, Any]:
    """Run a single working session on one project."""
    del max_iterations
    logger.info("Starting session for project %s", project_id)
    result = agent._graph.invoke(_initial_state(project_id))
    return {
        "session_id": result.get("session_id"),
        "feature_id": result.get("feature_id"),
        "phase": result.get("phase", SessionPhase.CLEANUP).value,
        "verification_result": result.get("verification_result"),
        "files_changed": result.get("files_changed", []),
        "error": result.get("error"),
    }