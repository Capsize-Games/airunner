"""Guard helpers for harness session execution."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import ProjectStatus


def project_error(project_id: int) -> dict[str, Any]:
    """Return a missing-project result for one run request."""
    return {"error": f"Project {project_id} not found"}


def project_status_result(project: Any) -> Optional[dict[str, Any]]:
    """Return a terminal result when the project cannot be worked on."""
    if project.status == ProjectStatus.COMPLETED:
        return {"message": "Project already completed", "status": "completed"}
    if project.status == ProjectStatus.ABANDONED:
        return {"error": "Project has been abandoned", "status": "abandoned"}
    return None
