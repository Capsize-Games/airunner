"""Feature lookup helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from airunner_services.database.models.project_state import (
    FeatureCategory,
    FeatureStatus,
    ProjectFeature,
    ProjectState,
)
from airunner_services.database.session import session_scope


def _project_by_id(db: Session, project_id: int) -> Optional[ProjectState]:
    """Return one project by id."""
    return db.query(ProjectState).filter(ProjectState.id == project_id).first()


def _feature_by_id(db: Session, feature_id: int) -> Optional[ProjectFeature]:
    """Return one feature by id."""
    return db.query(ProjectFeature).filter(ProjectFeature.id == feature_id).first()


def get_feature(
    manager: Any,
    feature_id: int,
) -> Optional[ProjectFeature]:
    """Get one feature by id."""
    with session_scope() as db:
        return manager._detach(db, _feature_by_id(db, feature_id))


def get_project_features(
    manager: Any,
    project_id: int,
    status: Optional[FeatureStatus] = None,
    category: Optional[FeatureCategory] = None,
) -> list[ProjectFeature]:
    """Get project features with optional filters."""
    with session_scope() as db:
        query = db.query(ProjectFeature).filter(
            ProjectFeature.project_id == project_id
        )
        if status is not None:
            query = query.filter(ProjectFeature.status == status)
        if category is not None:
            query = query.filter(ProjectFeature.category == category)
        features = query.order_by(ProjectFeature.priority.desc()).all()
        return manager._detach_all(db, features)


# Lookup helpers isolate the query shapes that other project-manager helpers
# reuse across progress, scheduling, and reporting flows.
# Detach calls remain local so callers always receive session-safe objects.