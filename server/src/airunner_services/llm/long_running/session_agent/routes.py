"""Routing and formatting helpers for the long-running Session Agent."""

from __future__ import annotations

from typing import Any

from airunner_services.database.models.project_state import (
    FeatureStatus,
    ProjectFeature,
)


def _status_icon(feature: ProjectFeature) -> str:
    """Return the display icon for one feature status."""
    return {
        FeatureStatus.PASSING: "✅",
        FeatureStatus.FAILING: "❌",
        FeatureStatus.IN_PROGRESS: "🔄",
        FeatureStatus.NOT_STARTED: "⬜",
        FeatureStatus.BLOCKED: "🚫",
    }.get(feature.status, "⬜")


def _summary_line(features: list[ProjectFeature]) -> str:
    """Return the summary line for the feature list."""
    total = len(features)
    passing = sum(
        1 for feature in features if feature.status == FeatureStatus.PASSING
    )
    percent = passing * 100 // total if total else 0
    return f"Total: {total} features, {passing} passing ({percent}%)\n"


def format_feature_list(agent: Any, features: list[ProjectFeature]) -> str:
    """Format the feature list for planning context."""
    del agent
    if not features:
        return "No features defined yet"
    lines = [_summary_line(features)]
    for feature in features:
        status = feature.status.value if feature.status else "not_started"
        lines.append(
            f"{_status_icon(feature)} [{status}] {feature.name} "
            f"(priority: {feature.priority})"
        )
    return "\n".join(lines)


def route_after_planning(agent: Any, state: dict[str, Any]) -> str:
    """Route after planning phase."""
    del agent
    return "end" if not state.get("feature_id") else "implement"


def route_after_implementation(agent: Any, state: dict[str, Any]) -> str:
    """Route after implementation phase."""
    del agent
    if state.get("error"):
        return "end"
    return "continue" if state.get("should_continue") else "verify"


def route_after_verification(agent: Any, state: dict[str, Any]) -> str:
    """Route after verification phase."""
    del agent
    if state.get("verification_result") == "passed":
        return "done"
    return "fix" if state.get("should_continue") else "done"


# Routing helpers stay pure so graph transitions are easy to review and reuse.
# Formatting helpers live beside them because the planning phase consumes the
# same feature-list presentation logic.
