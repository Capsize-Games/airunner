"""Run and finalization helpers for the initializer agent."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.llm.long_running.initializer_agent_state import (
    INITIALIZER_SYSTEM_PROMPT,
    InitializerWorkflowState,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def finalize(agent: Any, state: InitializerWorkflowState) -> dict[str, Any]:
    """Finalize one initializer run."""
    if state.get("error"):
        logger.error("Initialization failed: %s", state["error"])
    else:
        logger.info(
            "Project %s initialized successfully",
            state.get("project_id"),
        )
    return {}


def _initial_state(
    name: str,
    description: str,
    working_directory: Optional[str],
) -> InitializerWorkflowState:
    """Return the initial workflow state for project initialization."""
    return {
        "messages": [],
        "project_name": name,
        "project_description": description,
        "working_directory": working_directory,
        "features_json": None,
        "project_id": None,
        "error": None,
    }


def _result_payload(agent: Any, result: dict[str, Any], name: str) -> dict[str, Any]:
    """Build the public response for one initialized project."""
    project = agent._project_manager.get_project(result["project_id"])
    feature_count = project.total_features if project else 0
    return {
        "project_id": result["project_id"],
        "feature_count": feature_count,
        "project_name": name,
        "status": "initialized",
    }


def initialize_project(
    agent: Any,
    name: str,
    description: str,
    working_directory: Optional[str] = None,
) -> dict[str, Any]:
    """Initialize one long-running project."""
    logger.info("Starting project initialization: %s", name)
    result = agent._graph.invoke(_initial_state(name, description, working_directory))
    if result.get("error"):
        return {"error": result["error"]}
    return _result_payload(agent, result, name)


def get_feature_list_prompt(description: str) -> str:
    """Return the feature-list prompt for debugging and inspection."""
    return f"""{INITIALIZER_SYSTEM_PROMPT}

PROJECT REQUIREMENTS:
{description}

Generate the comprehensive feature list in JSON format."""