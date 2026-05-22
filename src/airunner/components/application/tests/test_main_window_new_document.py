"""Tests for new document entry from the main window."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.application.gui.windows.main.main_window import (
    MainWindow,
)


def test_art_action_new_uses_canvas_new_document_flow():
    """The main window should delegate new documents to the canvas widget."""
    canvas = SimpleNamespace(start_new_document_flow=Mock())
    window = SimpleNamespace(
        _ensure_canvas_loaded=Mock(),
        canvas=canvas,
        logger=Mock(),
    )

    MainWindow.on_artActionNew_triggered(window)

    window._ensure_canvas_loaded.assert_called_once_with()
    canvas.start_new_document_flow.assert_called_once_with()