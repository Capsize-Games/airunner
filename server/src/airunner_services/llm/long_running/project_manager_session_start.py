"""Session-start helpers for the long-running project manager."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from airunner_services.database.models.project_state import (
    FeatureStatus,
    SessionState,
)
from airunner_services.database.session import session_scope
from airunner_services.llm.long_running.project_manager_feature_lookup import (
    _feature_by_id,
)
from airunner_services.llm.long_running.project_manager_project_queries import (
    _project_by_id,
)


def _selected_feature_id(
    manager: Any,
    project_id: int,
    feature_id: Optional[int],
) -> Optional[int]:
    """Return the selected feature id for one session."""
    if feature_id is not None:
        return feature_id
    feature = manager.get_next_feature_to_work_on(project_id)
    return feature.id if feature is not None else None


def _mark_feature_in_progress(db: Session, feature_id: Optional[int]) -> None:
    """Mark one selected feature as in progress."""
    if feature_id is None:
        return
    feature = _feature_by_id(db, feature_id)
    if feature is not None:
        feature.status = FeatureStatus.IN_PROGRESS


def _session_record(
    project_id: int,
    feature_id: Optional[int],
    context_snapshot: Optional[dict[str, Any]],
) -> SessionState:
    """Build one session ORM record."""
    return SessionState(
        project_id=project_id,
        feature_id=feature_id,
        context_snapshot=context_snapshot or {},
        started_at=datetime.utcnow(),
    )


def start_session(
    manager: Any,
    project_id: int,
    feature_id: Optional[int] = None,
    context_snapshot: Optional[dict[str, Any]] = None,
) -> SessionState:
    """Start one working session."""
    with session_scope() as db:
        selected_feature_id = _selected_feature_id(
            manager, project_id, feature_id
        )
        _mark_feature_in_progress(db, selected_feature_id)
        session = _session_record(
            project_id, selected_feature_id, context_snapshot
        )
        db.add(session)
        if (project := _project_by_id(db, project_id)) is not None:
            project.current_feature_id = selected_feature_id
        db.commit()
        db.refresh(session)
        manager._logger.info(
            "Started session %s for project %s, feature %s",
            session.id,
            project_id,
            selected_feature_id,
        )
        return manager._detach(db, session)


# Session-start persistence stays here so callers only need one entrypoint for
# feature selection, in-progress marking, and session-row creation.
# Feature lookup and project lookup are imported from shared helpers to keep
# query behavior consistent with the rest of the project manager.
