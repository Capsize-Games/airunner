"""Unit tests for coding workspace shell support helpers."""

from airunner.components.document_editor.workspace_shell_support import (
    active_document_summary,
    bottom_panel_definitions,
    side_panel_definitions,
    workspace_roots_summary,
)


def test_workspace_shell_panel_keys_are_unique():
    """Workspace shell panel keys should stay unique across regions."""
    panel_keys = [panel.key for panel in side_panel_definitions()]
    panel_keys.extend(panel.key for panel in bottom_panel_definitions())

    assert len(panel_keys) == len(set(panel_keys))


def test_workspace_roots_summary_lists_all_roots():
    """Workspace root summaries should render every configured root."""
    summary = workspace_roots_summary(["/tmp/project", "/tmp/shared"])

    assert "Workspace roots:" in summary
    assert "- /tmp/project" in summary
    assert "- /tmp/shared" in summary


def test_active_document_summary_handles_missing_document():
    """Review summaries should have a sensible empty state."""
    assert active_document_summary(None) == "No active document selected yet."