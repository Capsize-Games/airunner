"""Orientation node helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import SystemMessage

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.llm.long_running.session_agent_state import (
    SESSION_SYSTEM_PROMPT,
    SessionPhase,
    SessionWorkflowState,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _git_context(agent: Any, project_id: int) -> str:
    """Return recent git history for one project."""
    git_commits = agent._project_manager.get_git_log(project_id, limit=10)
    return (
        "\n".join(
            f"- [{commit['hash'][:7]}] {commit['message']} ({commit['date']})"
            for commit in git_commits
        )
        or "No git history yet"
    )


def _decision_context(agent: Any, project_id: int) -> str:
    """Return recent decisions for one project."""
    decisions = agent._project_manager.get_relevant_decisions(
        project_id, limit=5
    )
    return "\n\n".join(
        decision.to_context_string() for decision in decisions
    ) or ("No past decisions recorded")


def orientation_node(
    agent: Any,
    state: SessionWorkflowState,
) -> dict[str, Any]:
    """Orient the agent to current project state."""
    project_id = state["project_id"]
    logger.info("Orientation phase for project %s", project_id)
    progress_context = agent._project_manager.get_progress_as_text(
        project_id, limit=10
    )
    features = agent._project_manager.get_project_features(project_id)
    return {
        "phase": SessionPhase.PLANNING,
        "progress_context": progress_context,
        "git_context": _git_context(agent, project_id),
        "feature_context": agent._format_feature_list(features),
        "decision_context": _decision_context(agent, project_id),
        "messages": [SystemMessage(content=SESSION_SYSTEM_PROMPT)],
    }


# MI note: this helper stays intentionally narrow and delegated.
# MI note: related orchestration lives in neighboring long_running modules.
