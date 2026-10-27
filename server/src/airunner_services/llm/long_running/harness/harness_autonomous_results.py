"""Terminal result builders for autonomous harness sessions."""

from __future__ import annotations

from typing import Any


def missing_project_result(sessions_run: int) -> dict[str, Any]:
    """Return the terminal result for a missing project."""
    return {
        "status": "error",
        "error": "Project not found",
        "sessions_run": sessions_run,
    }


def completed_result(sessions_run: int, project: Any) -> dict[str, Any]:
    """Return the terminal result for a completed project."""
    return {
        "status": "completed",
        "sessions_run": sessions_run,
        "features_passing": project.passing_features,
        "total_features": project.total_features,
    }


def repeated_error_result(
    error: str,
    sessions_run: int,
    project: Any,
) -> dict[str, Any]:
    """Return the terminal result for a repeated session failure."""
    return {
        "status": "error",
        "error": f"Repeated error: {error}",
        "sessions_run": sessions_run,
        "features_passing": project.passing_features,
        "total_features": project.total_features,
    }


def incomplete_result(
    project: Any,
    max_sessions: int,
    sessions_run: int,
) -> dict[str, Any]:
    """Return the terminal result when the session cap is reached."""
    return {
        "status": "incomplete",
        "message": f"Reached max sessions ({max_sessions})",
        "sessions_run": sessions_run,
        "features_passing": project.passing_features if project else 0,
        "total_features": project.total_features if project else 0,
    }
