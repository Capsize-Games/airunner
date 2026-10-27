"""Delegation helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from airunner_services.database.models.project_state import ProjectFeature
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _sub_context(
    state: dict[str, Any], feature: ProjectFeature
) -> dict[str, Any]:
    """Build the delegated sub-agent context."""
    return {
        "feature": feature.to_dict(),
        "project_context": state.get("progress_context", ""),
        "decision_context": state.get("decision_context", ""),
    }


def _record_delegation(
    agent: Any,
    state: dict[str, Any],
    feature: ProjectFeature,
    category: str,
) -> None:
    """Record the delegation choice for future sessions."""
    agent._project_manager.record_decision(
        project_id=state["project_id"],
        context=f"Implementing feature: {feature.name}",
        decision=f"Delegated to {category} sub-agent",
        reasoning=f"Feature category is {category}",
        feature_id=feature.id,
        tags=["delegation", category],
    )


def delegate_to_sub_agent(
    agent: Any,
    state: dict[str, Any],
    feature: ProjectFeature,
) -> dict[str, Any]:
    """Delegate implementation to a specialized sub-agent."""
    category = feature.category.value if feature.category else "functional"
    sub_agent = agent._sub_agents.get(category)
    if sub_agent is None:
        logger.warning(
            "No sub-agent for category %s, using main agent", category
        )
        return {}
    logger.info("Delegating to %s sub-agent", category)
    try:
        result = sub_agent.invoke(_sub_context(state, feature))
        _record_delegation(agent, state, feature, category)
        return {
            "tools_output": str(result),
            "messages": [
                AIMessage(content=f"Sub-agent ({category}) result:\n{result}")
            ],
        }
    except Exception as error:
        logger.error("Sub-agent delegation failed: %s", error)
        return {"error": f"Sub-agent failed: {error}"}


# MI note: this helper stays intentionally narrow and delegated.
# MI note: related orchestration lives in neighboring long_running modules.
