"""Focused tests for the coding workspace shell container."""

import os
import sys

from PySide6.QtWidgets import QApplication, QTabWidget

from airunner.components.document_editor.gui.widgets.document_editor_container_widget import (
    DocumentEditorContainerWidget,
)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _get_app() -> QApplication:
    """Return a QApplication instance for widget tests."""
    app = QApplication.instance()
    if app is not None:
        return app
    return QApplication([])


def test_document_editor_container_builds_workspace_shell_tabs():
    """The coding shell should wrap the explorer and terminal in tab sets."""
    _get_app()
    widget = DocumentEditorContainerWidget()

    assert isinstance(widget._workspace_side_tabs, QTabWidget)
    assert isinstance(widget._workspace_bottom_tabs, QTabWidget)
    assert widget._workspace_side_tabs.tabText(0) == "Explorer"
    assert widget._workspace_bottom_tabs.tabText(0) == "Terminal"
    assert widget._workspace_panel_tabs["project-search"][0] is widget._workspace_side_tabs
    assert widget._workspace_panel_tabs["problems"][0] is widget._workspace_bottom_tabs
    widget.deleteLater()


def test_run_script_starts_integrated_terminal_session(tmp_path):
    """Running a Python document should delegate into the terminal manager."""
    _get_app()
    widget = DocumentEditorContainerWidget()
    document_path = tmp_path / "demo.py"
    document_path.write_text("print('hello')\n", encoding="utf-8")
    captured = {}

    def fake_start(argv, working_directory=None, temp_file_path=None):
        captured["argv"] = argv
        captured["working_directory"] = working_directory
        captured["temp_file_path"] = temp_file_path
        return "session-1"

    widget.start_terminal_session = fake_start
    widget.run_script({"document_path": str(document_path)})

    assert captured["argv"] == [sys.executable, str(document_path)]
    assert captured["working_directory"] == str(tmp_path)
    assert captured["temp_file_path"] is None
    widget.deleteLater()