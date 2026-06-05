"""Project-creation helpers for the initializer agent."""

from __future__ import annotations

import json
from typing import Any

from airunner_services.database.models.project_state import ProjectStatus
from airunner_services.llm.long_running.initializer_agent_feature_records import (
    create_feature_records,
    update_feature_dependencies,
)
from airunner_services.llm.long_running.initializer_agent_state import (
    INITIALIZER_SYSTEM_PROMPT,
    InitializerWorkflowState,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _create_project_record(agent: Any, state: InitializerWorkflowState) -> Any:
    """Create one project record for initialization."""
    return agent._project_manager.create_project(
        name=state["project_name"],
        description=state["project_description"],
        working_directory=state.get("working_directory"),
        system_prompt=INITIALIZER_SYSTEM_PROMPT,
        init_git=True,
    )


def _load_features(state: InitializerWorkflowState) -> list[dict[str, Any]]:
    """Load feature definitions from the workflow state."""
    return json.loads(state["features_json"] or "[]")


def _activate_project(agent: Any, project_id: int, feature_count: int) -> None:
    """Activate one project and log its initialization."""
    agent._project_manager.update_project_status(
        project_id, ProjectStatus.ACTIVE
    )
    agent._project_manager.log_progress(
        project_id=project_id,
        action="Project initialized",
        outcome=f"Created project with {feature_count} features",
        git_commit=True,
    )


def create_project(
    agent: Any,
    state: InitializerWorkflowState,
) -> dict[str, Any]:
    """Create one project and its initial feature set."""
    logger.info("Creating project: %s", state["project_name"])
    if state.get("error"):
        return {}
    try:
        project = _create_project_record(agent, state)
        features_data = _load_features(state)
        feature_ids = create_feature_records(agent, project.id, features_data)
        update_feature_dependencies(agent, features_data, feature_ids)
        _activate_project(agent, project.id, len(features_data))
        return {"project_id": project.id}
    except Exception as error:
        logger.error("Project creation failed: %s", error)
        return {"error": str(error)}


# Project creation keeps the top-level initializer transaction narrow while
# feature-record details live in a dedicated helper module.
# That split keeps orchestration readable without duplicating feature logic.
