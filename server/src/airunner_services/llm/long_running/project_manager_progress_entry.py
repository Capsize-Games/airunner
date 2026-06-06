"""Progress-entry creation helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from airunner_services.database.models.project_state import (
    ProgressEntry,
    ProjectState,
)
from airunner_services.database.session import session_scope


def _project_by_id(db: Session, project_id: int) -> Optional[ProjectState]:
    """Return one project by id."""
    return db.query(ProjectState).filter(ProjectState.id == project_id).first()


def _commit_hash(
    manager: Any,
    db: Session,
    project_id: int,
    action: str,
    outcome: str,
    files_changed: Optional[list[str]],
    git_commit: bool,
) -> Optional[str]:
    """Return a git commit hash when the caller requests one."""
    if not git_commit:
        return None
    project = _project_by_id(db, project_id)
    if project is None or not project.git_repo_path:
        return None
    return manager._git_commit(
        project.git_repo_path,
        f"{action}\n\n{outcome}",
        files_changed or [],
    )


def _progress_entry(
    manager: Any,
    db: Session,
    project_id: int,
    action: str,
    outcome: str,
    session_id: Optional[int],
    feature_id: Optional[int],
    files_changed: Optional[list[str]],
    git_commit: bool,
    tokens_used: int,
) -> ProgressEntry:
    """Build one progress-entry ORM record."""
    return ProgressEntry(
        project_id=project_id,
        session_id=session_id,
        feature_id=feature_id,
        action=action,
        outcome=outcome,
        files_changed=files_changed or [],
        git_commit_hash=_commit_hash(
            manager, db, project_id, action, outcome, files_changed, git_commit
        ),
        tokens_used=tokens_used,
    )


def log_progress(
    manager: Any,
    project_id: int,
    action: str,
    outcome: str,
    session_id: Optional[int] = None,
    feature_id: Optional[int] = None,
    files_changed: Optional[list[str]] = None,
    git_commit: bool = False,
    tokens_used: int = 0,
) -> ProgressEntry:
    """Log one progress entry for a project."""
    with session_scope() as db:
        entry = _progress_entry(
            manager,
            db,
            project_id,
            action,
            outcome,
            session_id,
            feature_id,
            files_changed,
            git_commit,
            tokens_used,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        manager._logger.info("Logged progress: %s", action)
        return manager._detach(db, entry)

    # Progress-entry helpers isolate ORM construction from the public logging API.
    # Git commit creation stays nested here because it is part of one persisted
    # progress event.
    # Callers only see a detached entry once the database write is complete.
