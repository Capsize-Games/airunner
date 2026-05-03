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
        _schedule_centered_canvas_restore=Mock(),
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
    widget._schedule_centered_canvas_restore.assert_called_once_with()
    process_events.assert_not_called()


def test_schedule_centered_canvas_restore_is_deferred(monkeypatch):
    """Centered startup sync is queued after splitter changes settle."""
    scheduled = []
    widget = SimpleNamespace(
        _centered_canvas_restore_scheduled=False,
        _should_restore_centered_canvas=Mock(return_value=True),
        _restore_centered_canvas_after_splitter=Mock(),
        ui=SimpleNamespace(
            canvas_container=SimpleNamespace(
                _is_restoring_state=True,
                _needs_recenter_on_show=True,
            )
        ),
    )

    monkeypatch.setattr(
        module.QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    CanvasWidget._schedule_centered_canvas_restore(widget)

    assert widget._centered_canvas_restore_scheduled is True
    assert scheduled == [(0, widget._restore_centered_canvas_after_splitter)]


def test_restore_centered_canvas_after_splitter_previews_when_restoring():
    """Centered startup sync should refresh the preview during restore."""
    view = SimpleNamespace(
        _is_restoring_state=True,
        _needs_recenter_on_show=True,
        _preview_centered_layout=Mock(),
    )
    widget = SimpleNamespace(
        _centered_canvas_restore_scheduled=True,
        _should_restore_centered_canvas=Mock(return_value=True),
        update_grid_info=Mock(),
        ui=SimpleNamespace(canvas_container=view),
    )

    CanvasWidget._restore_centered_canvas_after_splitter(widget)

    assert widget._centered_canvas_restore_scheduled is False
    view._preview_centered_layout.assert_called_once_with()
    widget.update_grid_info.assert_called_once_with({})


def test_restore_centered_canvas_after_splitter_recenters_live_view():
    """Centered startup sync should recenter once restore is complete."""
    view = SimpleNamespace(
        _is_restoring_state=False,
        _initialized=True,
        on_recenter_grid_signal=Mock(),
    )
    widget = SimpleNamespace(
        _centered_canvas_restore_scheduled=True,
        _should_restore_centered_canvas=Mock(return_value=True),
        update_grid_info=Mock(),
        ui=SimpleNamespace(canvas_container=view),
    )

    CanvasWidget._restore_centered_canvas_after_splitter(widget)

    assert widget._centered_canvas_restore_scheduled is False
    view.on_recenter_grid_signal.assert_called_once_with()
    widget.update_grid_info.assert_called_once_with({})