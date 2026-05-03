"""Focused tests for the coding workspace shell container."""

import os

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