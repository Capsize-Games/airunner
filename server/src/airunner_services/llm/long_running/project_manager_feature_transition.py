"""Feature status-transition helpers for the project manager."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from airunner_services.database.models.project_state import (
    FeatureStatus,
    ProjectFeature,
    ProjectState,
    ProjectStatus,
)


def _apply_feature_status(
    feature: ProjectFeature,
    status: FeatureStatus,
    error: Optional[str],
) -> FeatureStatus:
    """Apply one new feature status and return the previous status."""
    old_status = feature.status
    feature.status = status
    feature.updated_at = datetime.utcnow()
    if status == FeatureStatus.FAILING:
        feature.attempts = (feature.attempts or 0) + 1
        feature.last_error = error
    elif status == FeatureStatus.PASSING:
        feature.last_error = None
    return old_status


def _update_project_passing_count(
    project: ProjectState,
    old_status: FeatureStatus,
    new_status: FeatureStatus,
) -> None:
    """Update the project's passing-feature count."""
    gained_pass = old_status != FeatureStatus.PASSING
    lost_pass = old_status == FeatureStatus.PASSING
    if gained_pass and new_status == FeatureStatus.PASSING:
        project.passing_features = (project.passing_features or 0) + 1
    elif lost_pass and new_status != FeatureStatus.PASSING:
        project.passing_features = max(0, (project.passing_features or 0) - 1)


def _maybe_complete_project(manager: Any, project: ProjectState) -> None:
    """Mark the project complete when all features are passing."""
    all_passing = project.total_features == project.passing_features
    if project.total_features and all_passing:
        project.status = ProjectStatus.COMPLETED
        manager._logger.info(
            "Project %s completed! All features passing.",
            project.id,
        )


# Transition helpers isolate status math from the persistence layer that calls
# them.
# Keeping the passing-count rules here avoids duplicating completion logic.
# Project completion remains a derived effect of feature state, not a caller rule.
