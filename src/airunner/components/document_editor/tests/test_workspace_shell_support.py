"""Unit tests for coding workspace shell support helpers."""

from airunner.components.document_editor.workspace_shell_support import (
    active_document_summary,
    bottom_panel_definitions,
    generated_write_review_summary,
    generated_write_review_text,
    python_diagnostics_summary,
    python_workflow_summary,
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


def test_generated_write_review_summary_renders_entries():
    """Generated-write review summaries should list persisted entries."""
    summary = generated_write_review_summary(
        [
            {
                "record_id": "write-1",
                "summary": "Edited workspace:src/app.py (+1/-1 lines).",
            }
        ]
    )

    assert "Generated writes:" in summary
    assert "write-1" in summary


def test_generated_write_review_text_includes_diff_preview():
    """Review text should append a diff preview when provided."""
    text = generated_write_review_text(
        "Edited workspace:src/app.py (+1/-1 lines).",
        "--- workspace:src/app.py\n+++ workspace:src/app.py",
    )

    assert "Diff:" in text
    assert "+++ workspace:src/app.py" in text


def test_python_workflow_summary_lists_quality_commands():
    """Problems-panel summaries should render Python workflow commands."""
    summary = python_workflow_summary(
        {
            "python_environment": {"manager": "venv"},
            "bootstrap_command": "python -m pip install -e .[dev]",
            "commands": {
                "tests": "python -m pytest",
                "lint": "python quality_report.py --path .",
                "format": "python -m ruff format .",
                "diagnostics": "python quality_report.py --path . --json",
            },
        }
    )

    assert "Python workflow (venv):" in summary
    assert "- tests: python -m pytest" in summary
    assert "- format: python -m ruff format ." in summary


def test_python_diagnostics_summary_renders_counts():
    """Problems-panel summaries should render Python diagnostics counts."""
    summary = python_diagnostics_summary(
        {
            "summary": {
                "files_checked": 2,
                "issue_count": 3,
                "error_count": 1,
                "warning_count": 2,
                "quality_report_enabled": True,
                "quality_report_issue_count": 2,
            }
        }
    )

    assert "Python diagnostics:" in summary
    assert "- files checked: 2" in summary
    assert "- quality report: 2 issue(s)" in summary