"""Tests for chat prompt show-event startup helpers."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import Qt

from airunner.components.chat.gui.widgets import chat_prompt_widget as module
from airunner.components.chat.gui.widgets.chat_prompt_widget import (
    ChatPromptWidget,
)


def test_chat_prompt_splitter_restore_is_deferred(monkeypatch):
    """The chat splitter restore is queued once after showEvent."""
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

    ChatPromptWidget._schedule_default_splitter_settings(widget)
    ChatPromptWidget._schedule_default_splitter_settings(widget)

    assert widget._default_splitter_settings_applied is True
    assert scheduled == [(0, widget._apply_default_splitter_settings)]


def test_chat_prompt_splitter_restore_does_not_process_events(monkeypatch):
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

    ChatPromptWidget._apply_default_splitter_settings(widget)

    widget.load_splitter_settings.assert_called_once_with(
        orientations={"chat_prompt_splitter": Qt.Orientation.Vertical},
        default_maximize_config={
            "chat_prompt_splitter": {
                "index_to_maximize": 0,
                "min_other_size": 50,
            }
        },
    )
    process_events.assert_not_called()