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


def agent_activity_entry(action: str, subject: str) -> str:
    """Return a one-line activity entry for the agent panel."""
    return f"{action}: {subject}"


def problem_entry(message: str) -> str:
    """Return a one-line problem entry for the problems panel."""
    return f"Problem: {message}"