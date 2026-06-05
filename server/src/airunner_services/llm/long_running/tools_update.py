"""Update tools for long-running project management."""

from __future__ import annotations

from typing import Optional

from airunner_services.database.models.project_state import FeatureStatus
from airunner_services.llm.core.tool_registry import ToolCategory, tool
from airunner_services.llm.long_running.tools_common import (
    error_message,
    feature_category,
    project_manager,
)


def _added_feature_message(
    name: str,
    feature_id: int,
    category: str,
    priority: int,
    step_count: int,
) -> str:
    """Return the add-feature success message."""
    return (
        f"Added feature '{name}' (ID: {feature_id})\n"
        f"Category: {category}\n"
        f"Priority: {priority}\n"
        f"Verification steps: {step_count}"
    )


@tool(
    name="add_project_feature",
    category=ToolCategory.PROJECT,
    description="Manually add a feature to a project.",
    requires_api=False,
)
def add_project_feature(
    project_id: int,
    name: str,
    description: str,
    category: str = "functional",
    priority: int = 5,
    verification_steps: Optional[list[str]] = None,
) -> str:
    """Add a feature to one project."""
    try:
        parsed_category = feature_category(category)
        steps = verification_steps or []
        feature = project_manager().add_feature(
            project_id=project_id,
            name=name,
            description=description,
            category=parsed_category,
            priority=priority,
            verification_steps=steps,
        )
        return _added_feature_message(
            name, feature.id, parsed_category.value, priority, len(steps)
        )
    except Exception as error:
        return error_message("Error adding feature", error)


@tool(
    name="update_feature_status",
    category=ToolCategory.PROJECT,
    description=(
        "Update the status of a project feature. "
        "IMPORTANT: Only mark as 'passing' after actual verification!"
    ),
    requires_api=False,
)
def update_feature_status(
    feature_id: int,
    status: str,
    error: Optional[str] = None,
) -> str:
    """Update the status of one feature."""
    try:
        parsed_status = FeatureStatus(status)
    except ValueError:
        return (
            f"Invalid status: {status}. Use: passing, failing, in_progress, "
            "not_started, blocked"
        )
    try:
        project_manager().update_feature_status(
            feature_id, parsed_status, error
        )
        return f"Feature {feature_id} status updated to: {status}"
    except Exception as exc:
        return error_message("Error updating status", exc)


@tool(
    name="log_project_progress",
    category=ToolCategory.PROJECT,
    description="Log progress on a project. Creates a record of work done.",
    requires_api=False,
)
def log_project_progress(
    project_id: int,
    action: str,
    outcome: str,
    files_changed: Optional[list[str]] = None,
    git_commit: bool = False,
) -> str:
    """Log progress on one project."""
    try:
        entry = project_manager().log_progress(
            project_id=project_id,
            action=action,
            outcome=outcome,
            files_changed=files_changed or [],
            git_commit=git_commit,
        )
        commit_msg = (
            f"\nGit commit: {entry.git_commit_hash[:7]}"
            if entry.git_commit_hash
            else ""
        )
        return f"Progress logged at {entry.timestamp}{commit_msg}"
    except Exception as error:
        return error_message("Error logging progress", error)


# Update tools remain the mutation-oriented counterpart to the read-only status
# tool surface.
# They translate user input into project-manager calls and return concise,
# operator-friendly result strings.
