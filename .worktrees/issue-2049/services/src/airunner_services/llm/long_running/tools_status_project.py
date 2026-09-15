"""Project-oriented status tools for long-running work."""

from __future__ import annotations

from typing import Optional

from airunner_services.llm.core.tool_registry import ToolCategory, tool
from airunner_services.llm.long_running.tools_common import (
    error_message,
    project_manager,
    project_status,
)
from airunner_services.llm.long_running.tools_status_formatting import (
    project_lines,
    status_breakdown,
)


@tool(
    name="get_project_status",
    category=ToolCategory.PROJECT,
    description="Get the current status and progress of a long-running project.",
    requires_api=False,
)
def get_project_status(project_id: int) -> str:
    """Get project status and progress."""
    try:
        manager = project_manager()
        project = manager.get_project(project_id)
        if project is None:
            return f"Project {project_id} not found"
        features = manager.get_project_features(project_id)
        progress = manager.get_progress_as_text(project_id, limit=5)
        return (
            f"# Project: {project.name}\n"
            f"**Status:** {project.status.value if project.status else 'unknown'}\n"
            f"**Progress:** {project.get_progress_summary()}\n\n"
            f"## Feature Breakdown:\n{status_breakdown(features)}\n\n"
            f"## Recent Progress:\n{progress}"
        )
    except Exception as error:
        return error_message("Error getting status", error)


@tool(
    name="get_project_progress_log",
    category=ToolCategory.PROJECT,
    description="Get the progress log for a project showing what has been done.",
    requires_api=False,
)
def get_project_progress_log(project_id: int, limit: int = 20) -> str:
    """Get the progress log for one project."""
    try:
        return project_manager().get_progress_as_text(project_id, limit=limit)
    except Exception as error:
        return error_message("Error getting progress", error)


@tool(
    name="list_long_running_projects",
    category=ToolCategory.PROJECT,
    description="List all long-running projects.",
    requires_api=False,
)
def list_long_running_projects(status_filter: Optional[str] = None) -> str:
    """List all long-running projects."""
    try:
        projects = project_manager().list_projects(
            status=project_status(status_filter)
        )
        if not projects:
            return "No projects found"
        return "\n".join(project_lines(projects))
    except Exception as error:
        return error_message("Error listing projects", error)


# Project-status tools stay read-only and assemble summaries from project-level
# query surfaces.
# Formatting helpers remain separate so text rendering can be reused by other
# tool modules without duplicating database calls.
