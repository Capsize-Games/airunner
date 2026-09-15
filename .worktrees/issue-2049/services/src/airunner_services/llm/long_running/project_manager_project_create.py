"""Project creation helpers for the long-running project manager."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from airunner_services.database.models.project_state import (
    ProjectState,
    ProjectStatus,
)
from airunner_services.database.session import session_scope


def _existing_project(db: Session, name: str) -> Optional[ProjectState]:
    """Return an existing project with the requested name."""
    return db.query(ProjectState).filter(ProjectState.name == name).first()


def _raise_if_project_exists(db: Session, name: str) -> None:
    """Raise when the requested project already exists."""
    if _existing_project(db, name) is not None:
        raise ValueError(f"Project '{name}' already exists")


def _git_repo_path(
    manager: Any,
    working_directory: Optional[str],
    init_git: bool,
) -> Optional[str]:
    """Return the initialized git path for one project."""
    if not working_directory:
        return None
    work_dir = Path(working_directory)
    work_dir.mkdir(parents=True, exist_ok=True)
    return manager._init_git_repo(work_dir) if init_git else None


def _project_record(
    manager: Any,
    name: str,
    description: str,
    working_directory: Optional[str],
    system_prompt: Optional[str],
    init_git: bool,
    metadata: Optional[dict[str, Any]],
) -> ProjectState:
    """Build one project ORM record."""
    return ProjectState(
        name=name,
        description=description,
        working_directory=working_directory,
        git_repo_path=_git_repo_path(manager, working_directory, init_git),
        status=ProjectStatus.INITIALIZING,
        system_prompt=system_prompt,
        project_metadata=metadata or {},
    )


def create_project(
    manager: Any, name: str, description: str,
    working_directory: Optional[str] = None,
    system_prompt: Optional[str] = None, init_git: bool = True,
    metadata: Optional[dict[str, Any]] = None,
) -> ProjectState:
    """Create a new long-running project."""
    with session_scope() as db:
        _raise_if_project_exists(db, name)
        project = _project_record(
            manager, name, description, working_directory,
            system_prompt, init_git, metadata,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        manager._logger.info("Created project '%s' (ID: %s)", name, project.id)
        return manager._detach(db, project)


    # Project creation keeps validation, git setup, and ORM record building on one
    # narrow surface.
    # Repository initialization is delegated so callers do not need to reason about
    # filesystem details here.
    # The detached return value keeps the public API session-safe.