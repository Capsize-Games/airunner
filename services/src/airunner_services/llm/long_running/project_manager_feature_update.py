"""Feature status-update helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import FeatureStatus
from airunner_services.database.session import session_scope
from airunner_services.llm.long_running.project_manager_feature_lookup import (
    _feature_by_id,
    _project_by_id,
)
from airunner_services.llm.long_running.project_manager_feature_transition import (
    _apply_feature_status,
    _maybe_complete_project,
    _update_project_passing_count,
)


def update_feature_status(
    manager: Any,
    feature_id: int,
    status: FeatureStatus,
    error: Optional[str] = None,
) -> None:
    """Update one feature status."""
    with session_scope() as db:
        feature = _feature_by_id(db, feature_id)
        if feature is None:
            return
        old_status = _apply_feature_status(feature, status, error)
        project = _project_by_id(db, feature.project_id)
        if project is not None:
            _update_project_passing_count(project, old_status, status)
            _maybe_complete_project(manager, project)
        db.commit()
        manager._logger.info("Feature %s status: %s", feature_id, status.value)


# The update path deliberately stays thin by delegating status math and lookups
# to neighboring helpers.
# That keeps persistence, transition rules, and logging on separate surfaces.
# Callers only need one entrypoint for feature-state changes.