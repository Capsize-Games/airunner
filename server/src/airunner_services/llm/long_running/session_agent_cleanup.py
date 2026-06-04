"""Cleanup node helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import FeatureStatus
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.llm.long_running.session_agent_state import (
    SessionPhase,
    SessionWorkflowState,
)


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _progress_result(
    agent: Any,
    feature_id: int,
    verification_result: Optional[str],
) -> tuple[str, str]:
    """Update the feature status and return progress text."""
    if verification_result == "passed":
        agent._project_manager.update_feature_status(feature_id, FeatureStatus.PASSING)
        return "Feature completed and verified", "All verification steps passed"
    agent._project_manager.update_feature_status(feature_id, FeatureStatus.FAILING)
    return "Feature attempted but needs more work", verification_result or (
        "Verification incomplete"
    )


def _next_action(agent: Any, project_id: int) -> str:
    """Return the next-session recommendation."""
    next_feature = agent._project_manager.get_next_feature_to_work_on(project_id)
    if next_feature is None:
        return "Project may be complete - review all features"
    return f"Work on: {next_feature.name}"


def _log_progress(
    agent: Any,
    state: SessionWorkflowState,
    feature_id: int,
    session_id: Optional[int],
    project_id: int,
    verification_result: Optional[str],
) -> None:
    """Log progress for the completed feature attempt."""
    action, outcome = _progress_result(agent, feature_id, verification_result)
    agent._project_manager.log_progress(
        project_id=project_id, session_id=session_id, feature_id=feature_id,
        action=action, outcome=outcome,
        files_changed=state.get("files_changed", []), git_commit=True,
    )


def cleanup_node(
    agent: Any, state: SessionWorkflowState,
) -> dict[str, Any]:
    """Clean up session and prepare for the next one."""
    logger.info("Cleanup phase")
    feature_id, session_id = state.get("feature_id"), state.get("session_id")
    project_id, verification_result = state["project_id"], state.get("verification_result")
    if feature_id is not None:
        _log_progress(
            agent, state, feature_id, session_id, project_id, verification_result
        )
    if session_id is not None:
        agent._project_manager.end_session(
            session_id=session_id,
            working_memory={
                "last_feature": feature_id,
                "verification_result": verification_result,
            },
            next_action=_next_action(agent, project_id),
        )
    return {"phase": SessionPhase.CLEANUP, "should_continue": False}


# Cleanup remains the point where feature status, progress logging, and session
# teardown are finalized together.
# That keeps the session graph phases simpler because they can stop once they
# produce implementation or verification output.
