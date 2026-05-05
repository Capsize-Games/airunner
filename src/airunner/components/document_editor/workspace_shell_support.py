"""Support helpers for AIRunner coding workspace shell panels."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkspaceShellPanelDefinition:
    """Definition for a workspace shell support panel."""

    key: str
    title: str
    placeholder: str


SIDE_PANEL_DEFINITIONS = (
    WorkspaceShellPanelDefinition(
        key="project-search",
        title="Search",
        placeholder=(
            "Project search results will appear here once the coding shell "
            "is wired to workspace search."
        ),
    ),
    WorkspaceShellPanelDefinition(
        key="review",
        title="Review",
        placeholder=(
            "Diff and review context will appear here while coding agents "
            "prepare edits."
        ),
    ),
    WorkspaceShellPanelDefinition(
        key="agent-activity",
        title="Agent Activity",
        placeholder=(
            "Agent status, delegated tasks, and high-level activity will "
            "appear here."
        ),
    ),
)

BOTTOM_PANEL_DEFINITIONS = (
    WorkspaceShellPanelDefinition(
        key="problems",
        title="Problems",
        placeholder=(
            "Problems and diagnostics will appear here when commands or "
            "validations report issues."
        ),
    ),
)


def side_panel_definitions() -> tuple[WorkspaceShellPanelDefinition, ...]:
    """Return the standard side-panel definitions."""
    return SIDE_PANEL_DEFINITIONS


def bottom_panel_definitions() -> tuple[WorkspaceShellPanelDefinition, ...]:
    """Return the standard bottom-panel definitions."""
    return BOTTOM_PANEL_DEFINITIONS


def workspace_roots_summary(root_paths: list[str]) -> str:
    """Return a human-readable workspace root summary."""
    if not root_paths:
        return "No workspace roots configured yet."
    lines = ["Workspace roots:"]
    for path in root_paths:
        lines.append(f"- {os.path.normpath(path)}")
    return "\n".join(lines)


def active_document_summary(file_path: str | None) -> str:
    """Return a review-panel summary for the active document."""
    if not file_path:
        return "No active document selected yet."
    return f"Active document:\n- {os.path.normpath(file_path)}"


def generated_write_review_summary(
    records: list[dict[str, object]],
) -> str:
    """Return a human-readable summary of generated writes for review."""
    if not records:
        return "No agent-generated writes recorded yet."
    lines = ["Generated writes:"]
    for record in records:
        summary = str(record.get("summary") or record.get("record_id"))
        record_id = record.get("record_id")
        lines.append(f"- {summary} [id: {record_id}]")
    return "\n".join(lines)


def generated_write_review_text(summary: str, diff_text: str | None) -> str:
    """Return review-panel text that combines a summary and diff preview."""
    if not diff_text:
        return summary
    return f"{summary}\n\nDiff:\n{diff_text}"


def python_workflow_summary(summary: dict[str, object]) -> str:
    """Return a problems-panel summary for Python workflow commands."""
    commands = summary.get("commands", {}) if isinstance(summary, dict) else {}
    environment = (
        summary.get("python_environment") if isinstance(summary, dict) else None
    )
    manager = "system"
    if isinstance(environment, dict) and environment.get("manager"):
        manager = str(environment["manager"])
    lines = [f"Python workflow ({manager}):"]
    bootstrap_command = summary.get("bootstrap_command")
    if bootstrap_command:
        lines.append(f"- bootstrap: {bootstrap_command}")
    for key in ("tests", "lint", "format", "diagnostics"):
        command = commands.get(key)
        if command:
            lines.append(f"- {key}: {command}")
    return "\n".join(lines)


def meeting_workflow_summary(summary: dict[str, object]) -> str:
    """Return a problems-panel summary for meeting workflow state."""
    commands = summary.get("commands", []) if isinstance(summary, dict) else []
    lines = ["Meeting workflow:"]
    if commands:
        joined = ", ".join(f"/{command}" for command in commands)
        lines.append(f"- chat commands: {joined}")
    lines.append(f"- meeting runs: {summary.get('meeting_run_count', 0)}")
    lines.append(f"- deliverable packs: {summary.get('deliverable_count', 0)}")
    lines.append(
        f"- packs needing review: {summary.get('review_required_count', 0)}"
    )
    title = str(summary.get("latest_deliverable_title") or "").strip()
    if title:
        status = str(summary.get("latest_review_status") or "pending")
        lines.append(f"- latest pack: {title} ({status})")
    return "\n".join(lines)


def python_diagnostics_summary(result: dict[str, object]) -> str:
    """Return a problems-panel summary for Python diagnostics results."""
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    lines = [
        "Python diagnostics:",
        f"- files checked: {summary.get('files_checked', 0)}",
        f"- issues: {summary.get('issue_count', 0)}",
        f"- errors: {summary.get('error_count', 0)}",
        f"- warnings: {summary.get('warning_count', 0)}",
    ]
    if summary.get("quality_report_enabled"):
        lines.append(
            "- quality report: "
            f"{summary.get('quality_report_issue_count', 0)} issue(s)"
        )
    return "\n".join(lines)


def agent_activity_entry(action: str, subject: str) -> str:
    """Return a one-line activity entry for the agent panel."""
    return f"{action}: {subject}"


def problem_entry(message: str) -> str:
    """Return a one-line problem entry for the problems panel."""
    return f"Problem: {message}"