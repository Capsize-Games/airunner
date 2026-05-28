"""Formatting helpers for long-running project status tools."""

from __future__ import annotations

from typing import Any


def status_counts(features: list[Any]) -> dict[str, int]:
    """Return feature counts grouped by status."""
    counts: dict[str, int] = {}
    for feature in features:
        status = feature.status.value if feature.status else "not_started"
        counts[status] = counts.get(status, 0) + 1
    return counts


def status_breakdown(features: list[Any]) -> str:
    """Return a formatted feature status breakdown."""
    return "\n".join(
        f"- {key}: {value}" for key, value in status_counts(features).items()
    )


def feature_lines(features: list[Any]) -> list[str]:
    """Return formatted lines for one feature list."""
    emoji = {
        "passing": "✅",
        "failing": "❌",
        "in_progress": "🔄",
        "not_started": "⬜",
        "blocked": "🚫",
    }
    lines = [f"# Features ({len(features)} total)\n"]
    for feature in features:
        status = feature.status.value if feature.status else "not_started"
        category = feature.category.value if feature.category else "functional"
        description = feature.description[:100]
        suffix = "..." if len(feature.description or "") > 100 else ""
        lines.append(
            f"{emoji.get(status, '⬜')} **{feature.name}** [{status}]\n"
            f"   Priority: {feature.priority} | Category: {category}\n"
            f"   {description}{suffix}"
        )
    return lines


def project_lines(projects: list[Any]) -> list[str]:
    """Return formatted lines for one project list."""
    lines = ["# Long-Running Projects\n"]
    for project in projects:
        status = project.status.value if project.status else "unknown"
        lines.append(
            f"**{project.name}** (ID: {project.id})\n"
            f"   Status: {status}\n"
            f"   Progress: {project.get_progress_summary()}\n"
            f"   Updated: {project.updated_at}\n"
        )
    return lines


def next_feature_steps(feature: Any) -> str:
    """Return formatted verification steps for one feature."""
    return "\n".join(
        f"- {step}" for step in (feature.verification_steps or [])
    )


# Formatting helpers stay separate from the registered tools so the same text
# building logic can support multiple status endpoints.
# These helpers are intentionally pure and operate on already-fetched records.
