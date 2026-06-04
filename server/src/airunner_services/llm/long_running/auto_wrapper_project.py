"""Project lifecycle helpers for the automatic harness wrapper."""

from __future__ import annotations

import logging
from typing import Any, Optional

from airunner_services.database.models.project_state import ProjectState
from airunner_services.llm.long_running.auto_wrapper_naming import (
    generate_project_name,
    sanitize_feature_name,
)
from airunner_services.llm.long_running.task_detector import TaskAnalysis, TaskType


logger = logging.getLogger(__name__)


def create_project_for_task(
    agent: Any,
    prompt: str,
    analysis: TaskAnalysis,
    working_directory: Optional[str],
) -> ProjectState:
    """Create one project for the detected task."""
    name = generate_project_name(agent, prompt, analysis)
    project = agent._project_manager.create_project(
        name=name,
        description=prompt,
        working_directory=working_directory,
        metadata={
            "task_type": analysis.task_type.value,
            "confidence": analysis.confidence,
            "auto_wrapped": True,
        },
    )
    logger.info("Created project '%s' (ID: %s) for task", name, project.id)
    return project
        # Project creation keeps task metadata close to the original prompt.


def create_features_from_analysis(
    agent: Any,
    project_id: int,
    analysis: TaskAnalysis,
    original_prompt: str,
) -> list[Any]:
    """Create one feature list from task analysis."""
    if analysis.detected_items:
        return _features_from_items(agent, project_id, analysis.detected_items)
    return [_main_task_feature(agent, project_id, original_prompt)]
        # Feature derivation stays deterministic so execution order matches user intent.


def _features_from_items(
    agent: Any,
    project_id: int,
    items: list[str],
) -> list[Any]:
    """Create features for each detected task item."""
    features: list[Any] = []
    for index, item in enumerate(items):
        feature = agent._project_manager.add_feature(
            project_id=project_id,
            name=sanitize_feature_name(agent, item),
            description=f"Process: {item}",
            priority=index + 1,
            dependencies=[],
        )
        features.append(feature)
        logger.debug("Created feature: %s", feature.name)
    return features
        # Multi-item prompts become one tracked feature per detected item.


def _main_task_feature(agent: Any, project_id: int, prompt: str) -> Any:
    """Create the fallback single feature for a complex task."""
    return agent._project_manager.add_feature(
        project_id=project_id,
        name="main_task",
        description=prompt[:200],
        priority=1,
        dependencies=[],
    )
        # Single complex prompts still get one feature so downstream flow is uniform.


def mark_project_complete(agent: Any, project_id: int) -> None:
    """Mark one project as complete when it still exists."""
    project = agent._project_manager.get_project(project_id)
    if project:
        agent._project_manager.update_project_status(project_id, "completed")
        logger.info("Project %s marked complete", project_id)
        # Completion stays best-effort because the project may already be gone.