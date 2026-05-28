"""Shared feature-record helpers for the long-running project manager."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from airunner_services.database.models.project_state import (
    FeatureCategory,
    FeatureStatus,
    ProjectFeature,
    ProjectState,
)


def _project_by_id(db: Session, project_id: int) -> Optional[ProjectState]:
    """Return one project by id."""
    return db.query(ProjectState).filter(ProjectState.id == project_id).first()


def _feature_record(
    project_id: int,
    name: str,
    description: str,
    category: FeatureCategory,
    verification_steps: Optional[list[str]],
    priority: int,
    depends_on: Optional[list[int]],
) -> ProjectFeature:
    """Build one feature ORM record."""
    return ProjectFeature(
        project_id=project_id,
        name=name,
        description=description,
        category=category,
        verification_steps=verification_steps or [],
        priority=priority,
        depends_on=depends_on or [],
        status=FeatureStatus.NOT_STARTED,
    )


def _increment_total_features(
    db: Session,
    project_id: int,
    amount: int,
) -> None:
    """Increment the stored feature count for one project."""
    project = _project_by_id(db, project_id)
    if project is not None:
        project.total_features = (project.total_features or 0) + amount


# These record builders keep ORM object construction separate from higher-level
# feature orchestration.
# Shared query helpers stay here so create and update paths reuse the same rows.
# Total-feature accounting remains local to the record-creation boundary.