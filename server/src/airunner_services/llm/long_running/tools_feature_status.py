"""Feature-oriented status tools for long-running work."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.llm.core.tool_registry import ToolCategory, tool
from airunner_services.llm.long_running.tools_common import (
    error_message,
    feature_status,
    project_manager,
)
from airunner_services.llm.long_running.tools_status_formatting import (
    feature_lines,
    next_feature_steps,
)


@tool(
    name="list_project_features",
    category=ToolCategory.PROJECT,
    description="List all features in a project with their status.",
    requires_api=False,
)
def list_project_features(
    project_id: int,
    status_filter: Optional[str] = None,
) -> str:
    """List features in one project."""
    try:
        features = project_manager().get_project_features(
            project_id,
            status=feature_status(status_filter),
        )
        if not features:
            return "No features found"
        return "\n".join(feature_lines(features))
    except Exception as error:
        return error_message("Error listing features", error)


def _feature_summary(feature: Any) -> str:
    """Return the detailed next-feature summary."""
    category = feature.category.value if feature.category else "functional"
    last_error = (
        f"## Last Error\n{feature.last_error}" if feature.last_error else ""
    )
    steps = next_feature_steps(feature) or "None specified"
    return (
        f"# Next Feature: {feature.name}\n\n"
        f"**ID:** {feature.id}\n"
        f"**Priority:** {feature.priority}\n"
        f"**Category:** {category}\n"
        f"**Attempts:** {feature.attempts or 0}\n\n"
        f"## Description\n{feature.description}\n\n"
        f"## Verification Steps\n{steps}\n\n{last_error}"
    )


@tool(
    name="get_next_feature_to_work_on",
    category=ToolCategory.PROJECT,
    description=(
        "Get the next feature that should be worked on in a project. "
        "Returns the highest priority feature with met dependencies."
    ),
    requires_api=False,
)
def get_next_feature_to_work_on(project_id: int) -> str:
    """Get the next feature that should be worked on."""
    try:
        feature = project_manager().get_next_feature_to_work_on(project_id)
        if feature is None:
            return "No features to work on - project may be complete!"
        return _feature_summary(feature)
    except Exception as error:
        return error_message("Error", error)


# Feature-status tools stay focused on the project feature list and the next
# actionable work item.
# Detailed feature formatting is delegated so these tools only assemble the
# operator-facing status response.
