"""Bulk feature-creation helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any

from airunner_services.database.models.project_state import (
    FeatureCategory,
    ProjectFeature,
)
from airunner_services.database.session import session_scope
from airunner_services.llm.long_running.project_manager_feature_records import (
    _feature_record,
    _increment_total_features,
)


def _feature_records(
    project_id: int,
    features: list[dict[str, Any]],
) -> list[ProjectFeature]:
    """Build feature records for one bulk insert."""
    records: list[ProjectFeature] = []
    for feature in features:
        records.append(
            _feature_record(
                project_id,
                feature["name"],
                feature.get("description", ""),
                FeatureCategory(feature.get("category", "functional")),
                feature.get("verification_steps"),
                feature.get("priority", 5),
                feature.get("depends_on"),
            )
        )
    return records


def add_features_bulk(
    manager: Any,
    project_id: int,
    features: list[dict[str, Any]],
) -> list[ProjectFeature]:
    """Add multiple features to one project."""
    with session_scope() as db:
        created = _feature_records(project_id, features)
        for feature in created:
            db.add(feature)
        _increment_total_features(db, project_id, len(created))
        db.commit()
        for feature in created:
            db.refresh(feature)
        manager._logger.info(
            "Added %s features to project %s",
            len(created),
            project_id,
        )
        return manager._detach_all(db, created)
