"""Project query and status helpers for the project manager."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from airunner_services.database.models.project_state import (
    ProjectState,
    ProjectStatus,
)
from airunner_services.database.session import session_scope


def _project_by_id(db: Session, project_id: int) -> Optional[ProjectState]:
    """Return one project by id."""
    return db.query(ProjectState).filter(ProjectState.id == project_id).first()


def _project_by_name(db: Session, name: str) -> Optional[ProjectState]:
    """Return one project by name."""
    return db.query(ProjectState).filter(ProjectState.name == name).first()


def get_project(manager: Any, project_id: int) -> Optional[ProjectState]:
    """Get one project by id."""
    with session_scope() as db:
        return manager._detach(db, _project_by_id(db, project_id))


def get_project_by_name(
    manager: Any,
    name: str,
) -> Optional[ProjectState]:
    """Get one project by name."""
    with session_scope() as db:
        return manager._detach(db, _project_by_name(db, name))


def list_projects(
    manager: Any,
    status: Optional[ProjectStatus] = None,
) -> list[ProjectState]:
    """List projects, optionally filtered by status."""
    with session_scope() as db:
        query = db.query(ProjectState)
        if status is not None:
            query = query.filter(ProjectState.status == status)
        projects = query.order_by(ProjectState.updated_at.desc()).all()
        return manager._detach_all(db, projects)


def update_project_status(
    manager: Any,
    project_id: int,
    status: ProjectStatus,
) -> None:
    """Update one project status."""
    with session_scope() as db:
        project = _project_by_id(db, project_id)
        if project is None:
            return
        project.status = status
        project.updated_at = datetime.utcnow()
        db.commit()
        manager._logger.info(
            "Project %s status updated to %s",
            project_id,
            status.value,
        )


def delete_project(manager: Any, project_id: int) -> bool:
    """Delete one project and related data."""
    with session_scope() as db:
        project = _project_by_id(db, project_id)
        if project is None:
            return False
        db.delete(project)
        db.commit()
        manager._logger.info("Deleted project %s", project_id)
        return True

    # Project query helpers keep lookup, listing, and status mutation on one shared
    # persistence boundary.
    # The detached-object pattern is repeated here so callers never depend on an
    # open session.
    # Deletion also stays local to the query module because it shares the same rows.
