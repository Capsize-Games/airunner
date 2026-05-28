"""Project-creation tools for long-running project management."""

from __future__ import annotations

from typing import Optional

from airunner_services.llm.core.tool_registry import ToolCategory, tool
from airunner_services.llm.long_running.tools_common import (
    error_message,
    project_manager,
)


@tool(
    name="create_long_running_project",
    category=ToolCategory.PROJECT,
    description=(
        "Create a new long-running project with automatic feature decomposition. "
        "The system will analyze requirements and create a comprehensive feature list."
    ),
    requires_api=False,
)
def create_long_running_project(
    name: str,
    description: str,
    working_directory: Optional[str] = None,
) -> str:
    """Create a new long-running project."""
    try:
        manager = project_manager()
        existing = manager.get_project_by_name(name)
        if existing:
            return f"Project '{name}' already exists (ID: {existing.id})"
        project = manager.create_project(name, description, working_directory)
        return (
            f"Created project '{name}' (ID: {project.id})\n"
            f"Working directory: {working_directory or 'Not set'}\n"
            "Status: Initializing\n\n"
            "Use 'initialize_project_features' to generate the feature list."
        )
    except Exception as error:
        return error_message("Error creating project", error)


@tool(
    name="initialize_project_features",
    category=ToolCategory.PROJECT,
    description=(
        "Initialize a project with a comprehensive feature list. "
        "Uses AI to analyze requirements and create atomic, testable features."
    ),
    requires_api=True,
)
def initialize_project_features(project_id: int) -> str:
    """Return instructions for feature initialization."""
    return (
        f"To initialize features for project {project_id}, use the "
        "LongRunningHarness.create_project() method which handles "
        "both project creation and feature initialization.\n\n"
        "Example:\n"
        "```python\n"
        "harness = LongRunningHarness(chat_model)\n"
        "project_id = harness.create_project(\n"
        "    name='My Project',\n"
        "    description='Build a...',\n"
        ")\n"
        "```"
    )