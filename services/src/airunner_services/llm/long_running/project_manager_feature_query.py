"""Feature-query helpers for the long-running project manager."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from airunner_services.database.models.project_state import (
    FeatureStatus,
    ProjectFeature,
)


def _project_features(db: Session, project_id: int) -> list[ProjectFeature]:
    """Return all features for one project."""
    query = db.query(ProjectFeature).filter(ProjectFeature.project_id == project_id)
    return query.all()


def _in_progress_feature(
    db: Session,
    project_id: int,
) -> Optional[ProjectFeature]:
    """Return the first in-progress feature for one project."""
    return (
        db.query(ProjectFeature)
        .filter(
            ProjectFeature.project_id == project_id,
            ProjectFeature.status == FeatureStatus.IN_PROGRESS,
        )
        .first()
    )