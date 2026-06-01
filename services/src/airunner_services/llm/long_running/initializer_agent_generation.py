"""Feature-generation helpers for the initializer agent."""

from __future__ import annotations

from typing import Any

from airunner_services.llm.long_running.initializer_agent_json import (
    extract_json_from_response,
)
from airunner_services.llm.long_running.initializer_agent_state import (
    InitializerWorkflowState,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def generate_features(
    agent: Any,
    state: InitializerWorkflowState,
) -> dict[str, Any]:
    """Generate one feature list from analyzed requirements."""
    logger.info("Generating feature list with LLM")
    try:
        response = agent._chat_model.invoke(state["messages"])
        features_json = extract_json_from_response(response.content)
        if not features_json:
            return {
                "error": "Failed to extract feature list from LLM response",
                "messages": [response],
            }
        return {"features_json": features_json, "messages": [response]}
    except Exception as error:
        logger.error("Feature generation failed: %s", error)
        return {"error": str(error)}