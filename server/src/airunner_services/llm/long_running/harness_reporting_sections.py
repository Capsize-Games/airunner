"""Section builders for long-running harness reports."""

from __future__ import annotations

from typing import Any

from airunner_services.database.models.project_state import FeatureStatus


def report_header(project: Any) -> list[str]:
    """Return the report header lines."""
    return [
        f"# Project Report: {project.name}",
        "",
        f"**Status:** {project.status.value if project.status else 'unknown'}",
        f"**Created:** {project.created_at}",
        f"**Last Updated:** {project.updated_at}",
        "",
        "## Description",
        project.description or "No description",
        "",
        f"## Progress: {project.get_progress_summary()}",
        "",
        "### Feature Status",
    ]


def feature_section(features: list[Any]) -> list[str]:
    """Return the feature-status section lines."""
    lines: list[str] = []
    for status in FeatureStatus:
        status_features = [
            feature for feature in features if feature.status == status
        ]
        if status_features:
            lines.append(f"\n#### {status.value.upper()}")
            lines.extend(f"- {feature.name}" for feature in status_features)
    return lines


def progress_section(progress_log: list[Any]) -> list[str]:
    """Return the progress-log section lines."""
    return [
        "",
        "## Progress Log",
        "",
        *[entry.to_log_string() for entry in progress_log],
    ]


def git_section(git_log: list[dict[str, str]]) -> list[str]:
    """Return the git-history section lines."""
    lines = ["", "## Git History", ""]
    lines.extend(
        f"- [{commit['hash'][:7]}] {commit['message']}" for commit in git_log
    )
    return lines


def decision_section(decisions: list[Any]) -> list[str]:
    """Return the decision-history section lines."""
    lines = ["", "## Decision History", ""]
    for decision in decisions:
        outcome = decision.outcome.value if decision.outcome else "pending"
        lines.append(
            f"- **{decision.decision_made}** ({outcome})\n"
            f"  Context: {decision.decision_context[:100]}...\n"
            f"  Lesson: {decision.lesson_learned or 'None'}"
        )
    return lines


# Report formatting helpers stay separate from project lookup so exports can
# reuse the same section builders.
# Each section keeps just enough context for a human-readable summary.
