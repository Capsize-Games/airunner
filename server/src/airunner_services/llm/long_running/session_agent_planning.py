"""Planning node helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from airunner_services.database.models.project_state import FeatureStatus
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.llm.long_running.session_agent_state import (
    SessionPhase,
    SessionWorkflowState,
)


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _planning_complete_message() -> AIMessage:
    """Return the terminal planning message when no features remain."""
    return AIMessage(
        content="PHASE: planning\nACTION: Checked feature list\n"
        "OUTCOME: All features are passing!\n"
        "NEXT: Project appears complete - verify and close"
    )


def _session_id(agent: Any, state: SessionWorkflowState, feature_id: int) -> int:
    """Ensure one session id exists for the selected feature."""
    session_id = state.get("session_id")
    if session_id is not None:
        return session_id
    session = agent._project_manager.start_session(
        project_id=state["project_id"],
        feature_id=feature_id,
    )
    return session.id


def _planning_prompt(feature: Any) -> str:
    """Return the planning prompt for the selected feature."""
    steps = "\n".join(f"- {step}" for step in (feature.verification_steps or []))
    last_error = f"**Last Error:** {feature.last_error}" if feature.last_error else ""
    category = feature.category.value if feature.category else "functional"
    return f"""# Planning Phase

I will work on this feature:

**Feature:** {feature.name}
**Category:** {category}
**Priority:** {feature.priority}
**Description:** {feature.description}

**Verification Steps:**
{steps}

**Previous Attempts:** {feature.attempts or 0}
{last_error}

---

PHASE: planning
ACTION: Selected feature to work on
OUTCOME: Will implement \"{feature.name}\"
NEXT: Begin implementation"""


def _planning_result(
    agent: Any,
    state: SessionWorkflowState,
    next_feature: Any,
) -> dict[str, Any]:
    """Build the state update for one selected feature."""
    session_id = _session_id(agent, state, next_feature.id)
    agent._project_manager.update_feature_status(next_feature.id, FeatureStatus.IN_PROGRESS)
    return {
        "phase": SessionPhase.IMPLEMENTATION,
        "feature_id": next_feature.id,
        "session_id": session_id,
        "should_continue": True,
        "messages": [HumanMessage(content=_planning_prompt(next_feature))],
    }


def planning_node(
    agent: Any,
    state: SessionWorkflowState,
) -> dict[str, Any]:
    """Plan what feature to work on."""
    logger.info("Planning phase")
    next_feature = agent._project_manager.get_next_feature_to_work_on(state["project_id"])
    if next_feature is None:
        logger.info("No features left to work on - project may be complete")
        return {
            "phase": SessionPhase.CLEANUP,
            "feature_id": None,
            "should_continue": False,
            "messages": [_planning_complete_message()],
        }
    return _planning_result(agent, state, next_feature)


# Planning owns feature selection and initial session creation for the current
# work cycle.
# The implementation and verification phases then consume the prepared state
# without repeating project-manager selection logic.
