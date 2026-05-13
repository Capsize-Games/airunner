"""Tests for canvas widget keyboard shortcuts and cursor updates."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.art.gui.widgets.canvas import canvas_widget as module
from airunner.components.art.gui.widgets.canvas.canvas_widget import (
    CanvasWidget,
)
from airunner.enums import CanvasToolName


class _FakeSignal:
    def __init__(self):
        self.connected = []

    def connect(self, handler):
        self.connected.append(handler)


class _FakeShortcut:
    def __init__(self, sequence, target):
        self.sequence = sequence
        self.target = target
        self.context = None
        self.auto_repeat = None
        self.activated = _FakeSignal()

    def setContext(self, context):
        self.context = context

    def setAutoRepeat(self, enabled):
        self.auto_repeat = enabled


def test_configure_canvas_shortcuts_registers_undo_and_redo(monkeypatch):
    """Canvas-local undo/redo shortcuts should be attached to the view."""
    created = []

    def fake_shortcut(sequence, target):
        shortcut = _FakeShortcut(sequence, target)
        created.append(shortcut)
        return shortcut

    monkeypatch.setattr(module, "QShortcut", fake_shortcut)
    monkeypatch.setattr(module, "QKeySequence", lambda value: value)

    view = object()
    widget = CanvasWidget.__new__(CanvasWidget)
    widget.ui = SimpleNamespace(canvas_container=view)
    widget.logger = Mock()

    CanvasWidget._configure_canvas_shortcuts(widget)

    assert [shortcut.sequence for shortcut in created] == [
        "Ctrl+Z",
        "Ctrl+Y",
        "Ctrl+Shift+Z",
    ]
    assert all(shortcut.target is view for shortcut in created)
    assert all(
        shortcut.context == module.Qt.WidgetWithChildrenShortcut
        for shortcut in created
    )
    assert all(shortcut.auto_repeat is False for shortcut in created)
    assert widget._canvas_shortcuts == created


def test_on_toggle_tool_signal_applies_cursor_for_active_tool():
    """Keyboard tool switches should request the matching canvas cursor."""
    widget = CanvasWidget.__new__(CanvasWidget)
    widget.update_application_settings = Mock()
    widget._update_action_buttons = Mock()
    widget._update_cursor = Mock()
    widget._update_status_labels = Mock()
    widget.api = SimpleNamespace(
        art=SimpleNamespace(canvas=SimpleNamespace(tool_changed=Mock()))
    )

    CanvasWidget.on_toggle_tool_signal(
        widget,
        {"tool": CanvasToolName.BRUSH, "active": True},
    )

    widget._update_cursor.assert_called_once_with(
        {
            "apply_cursor": True,
            "current_tool": CanvasToolName.BRUSH,
        }
    )