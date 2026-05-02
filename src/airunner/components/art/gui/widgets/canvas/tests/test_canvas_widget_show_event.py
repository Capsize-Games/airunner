"""Tests for canvas widget show-event startup helpers."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.art.gui.widgets.canvas import canvas_widget as module
from airunner.components.art.gui.widgets.canvas.canvas_widget import (
    CanvasWidget,
)


def test_canvas_splitter_restore_is_deferred(monkeypatch):
    """The canvas splitter restore is queued once after showEvent."""
    scheduled = []
    widget = SimpleNamespace(
        _default_splitter_settings_applied=False,
        _apply_default_splitter_settings=Mock(),
        isVisible=Mock(return_value=True),
    )

    monkeypatch.setattr(
        module.QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    CanvasWidget._schedule_default_splitter_settings(widget)
    CanvasWidget._schedule_default_splitter_settings(widget)

    assert widget._default_splitter_settings_applied is True
    assert scheduled == [(0, widget._apply_default_splitter_settings)]


def test_canvas_splitter_restore_does_not_process_events(monkeypatch):
    """The splitter restore avoids re-entering Qt from showEvent."""
    process_events = Mock(side_effect=AssertionError("re-entered Qt"))
    logger = Mock()
    ui = Mock()
    widget = SimpleNamespace(
        load_splitter_settings=Mock(),
        logger=logger,
        ui=ui,
    )

    monkeypatch.setattr(module.QApplication, "processEvents", process_events)

    CanvasWidget._apply_default_splitter_settings(widget)

    widget.load_splitter_settings.assert_called_once_with(
        default_maximize_config={
            "splitter": {"index_to_maximize": 1, "min_other_size": 50}
        },
    )
    process_events.assert_not_called()