"""Feature-state update helpers for the automatic wrapper."""

from __future__ import annotations

import logging
from typing import Any

from airunner_services.database.models.project_state import FeatureStatus


logger = logging.getLogger(__name__)


def mark_feature_in_progress(
    agent: Any,
    feature: Any,
    index: int,
    total_features: int,
) -> None:
    """Record the start of one feature execution."""
    agent._emit_progress(feature.name, "in_progress", index / total_features)
    agent._project_manager.update_feature_status(
        feature.id,
        FeatureStatus.IN_PROGRESS.value,
    )
        # Keep state transitions separate so the execution loop stays linear.


def mark_feature_success(
    agent: Any,
    feature: Any,
    index: int,
    total_features: int,
    project_id: int,
) -> None:
    """Record successful completion for one feature."""
    agent._project_manager.log_progress(
        project_id=project_id,
        feature_name=feature.name,
        message=f"Completed: {feature.description[:100]}",
        work_type="execution",
    )
    agent._project_manager.update_feature_status(
        feature.id,
        FeatureStatus.COMPLETED.value,
    )
    agent._emit_progress(feature.name, "completed", (index + 1) / total_features)
        # Success bookkeeping pairs persistence with the outward progress signal.


def mark_feature_failure(
    agent: Any,
    feature: Any,
    error: Exception,
    project_id: int,
) -> None:
    """Record failed execution for one feature."""
    logger.error("Feature %s failed: %s", feature.name, error)
    agent._project_manager.update_feature_status(
        feature.id,
        FeatureStatus.BLOCKED.value,
    )
    agent._project_manager.log_progress(
        project_id=project_id,
        feature_name=feature.name,
        message=f"Failed: {error}",
        work_type="error",
    )
        # Failure bookkeeping mirrors the success path with an error outcome.