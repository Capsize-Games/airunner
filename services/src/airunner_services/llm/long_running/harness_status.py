"""Status helpers for the long-running harness."""

from __future__ import annotations

from typing import Any

from airunner_services.llm.long_running.harness_status_summary import (
    recent_progress,
    status_counts,
)


def get_project_status(agent: Any, project_id: int) -> dict[str, Any]:
    """Get current project status and progress."""
    project = agent._project_manager.get_project(project_id)
    if project is None:
        return {"error": "Project not found"}
    features = agent._project_manager.get_project_features(project_id)
    progress_log = agent._project_manager.get_progress_log(project_id, 5)
    progress_percent = (project.passing_features / project.total_features * 100) if project.total_features else 0
    return {
        "project_id": project_id,
        "name": project.name,
        "status": project.status.value if project.status else "unknown",
        "total_features": project.total_features,
        "passing_features": project.passing_features,
        "progress_percent": progress_percent,
        "feature_breakdown": status_counts(features),
        "recent_progress": recent_progress(progress_log),
    }


# Status assembly remains read-only so callers can poll it freely without
# mutating project state.
# Derived percentages stay local to avoid storing redundant summary fields.