"""Project lifecycle helpers for the long-running harness."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _creation_result(
    agent: Any,
    name: str,
    description: str,
    working_directory: Optional[str],
) -> tuple[int, int]:
    """Initialize one project and return its id and feature count."""
    result = agent._initializer.initialize_project(
        name=name,
        description=description,
        working_directory=working_directory,
    )
    if result.get("error"):
        raise ValueError(f"Project initialization failed: {result['error']}")
    return result["project_id"], result["feature_count"]


def create_project(
    agent: Any,
    name: str,
    description: str,
    working_directory: Optional[str] = None,
) -> int:
    """Create and initialize a new project."""
    logger.info("Creating project: %s", name)
    project_id, feature_count = _creation_result(
        agent, name, description, working_directory
    )
    logger.info(
        "Project %s created with %s features", project_id, feature_count
    )
    if agent._on_progress:
        agent._on_progress(
            {
                "event": "project_created",
                "project_id": project_id,
                "feature_count": feature_count,
            }
        )
    return project_id
