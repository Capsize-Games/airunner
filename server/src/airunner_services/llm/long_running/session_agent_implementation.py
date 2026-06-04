"""Implementation node helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.llm.long_running.session_agent_state import (
    SessionPhase,
    SessionWorkflowState,
)


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _implementation_prompt(feature: Any) -> str:
    """Return the implementation prompt for one feature."""
    category = feature.category.value if feature.category else "functional"
    return f"""# Implementation Phase

Working on: {feature.name}
Category: {category}

Description: {feature.description}

Use your tools to implement this feature. Focus on:
1. Writing clean, well-documented code
2. Following project conventions
3. Making atomic, focused changes
4. Testing as you go

Report your progress after each significant action."""


def _implementation_complete(content: str) -> bool:
    """Return whether the implementation response looks complete."""
    phrases = [
        "implementation complete",
        "feature implemented",
        "ready for testing",
        "ready to verify",
    ]
    return any(phrase in content for phrase in phrases)


def _implementation_response(
    agent: Any,
    state: SessionWorkflowState,
    feature: Any,
) -> dict[str, Any]:
    """Invoke the model for one implementation step."""
    response = agent._chat_model.invoke(
        state["messages"] + [HumanMessage(content=_implementation_prompt(feature))]
    )
    complete = _implementation_complete(response.content.lower())
    return {
        "messages": [response],
        "tools_output": response.content,
        "files_changed": state.get("files_changed", []),
        "phase": SessionPhase.VERIFICATION if complete else SessionPhase.IMPLEMENTATION,
        "should_continue": not complete,
    }


def implementation_node(
    agent: Any,
    state: SessionWorkflowState,
) -> dict[str, Any]:
    """Implement the selected feature."""
    logger.info("Implementation phase for feature %s", state.get("feature_id"))
    feature = agent._project_manager.get_feature(state["feature_id"])
    if feature is None:
        return {"error": f"Feature {state['feature_id']} not found", "should_continue": False}
    if feature.category and feature.category.value in agent._sub_agents:
        return agent._delegate_to_sub_agent(state, feature)
    try:
        return _implementation_response(agent, state, feature)
    except Exception as error:
        logger.error("Implementation error: %s", error)
        return {"error": str(error), "should_continue": False}


# Implementation stays focused on one feature at a time.
# Prompt construction, completion detection, and sub-agent delegation remain in
# this phase helper so the SessionAgent facade only wires phase transitions.
# The implementation prompt also stays local because it uses the same feature
# fields that drive completion heuristics and delegation.
