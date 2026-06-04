"""Single-feature creation helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import (
    FeatureCategory,
    ProjectFeature,
)
from airunner_services.database.session import session_scope
from airunner_services.llm.long_running.project_manager_feature_records import (
    _feature_record,
    _increment_total_features,
)


def add_feature(
    manager: Any, project_id: int, name: str, description: str,
    category: FeatureCategory = FeatureCategory.FUNCTIONAL,
    verification_steps: Optional[list[str]] = None, priority: int = 5,
    depends_on: Optional[list[int]] = None,
) -> ProjectFeature:
    """Add one feature to a project."""
    with session_scope() as db:
        feature = _feature_record(
            project_id, name, description, category,
            verification_steps, priority, depends_on,
        )
        db.add(feature)
        _increment_total_features(db, project_id, 1)
        db.commit()
        db.refresh(feature)
        manager._logger.info("Added feature '%s' to project %s", name, project_id)
        return manager._detach(db, feature)