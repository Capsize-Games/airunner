import pytest
from unittest.mock import patch
from airunner.enums import CanvasToolName
from airunner.gui.widgets.canvas.logic.custom_view_logic import CustomViewLogic


class DummySettings:
    def __init__(self):
        self.current_tool = None


@pytest.fixture
def logic():
    settings = DummySettings()
    updates = []

    def update_application_settings(key, value):
        updates.append((key, value))
        setattr(settings, key, value)

    return (
        CustomViewLogic(settings, update_application_settings),
        settings,
        updates,
    )


@patch(
    "airunner.gui.cursors.circle_brush.circle_cursor",
    return_value="mock_cursor",
)
def test_get_cursor_brush_and_eraser(mock_circle_cursor, logic):
    view_logic, _, _ = logic
    cursor = view_logic.get_cursor(
        CanvasToolName.BRUSH, event=None, brush_size=20, apply_cursor=True
    )
    assert cursor == "mock_cursor"
    cursor2 = view_logic.get_cursor(
        CanvasToolName.ERASER, event=None, brush_size=20, apply_cursor=True
    )
    assert cursor2 == "mock_cursor"
    from PySide6.QtCore import Qt

    assert (
        view_logic.get_cursor(
            CanvasToolName.BRUSH, event=None, brush_size=20, apply_cursor=False
        )
        == Qt.CursorShape.ArrowCursor
    )


def test_get_cursor_text_and_grid(logic):
    view_logic, _, _ = logic
    from PySide6.QtCore import Qt

    assert (
        view_logic.get_cursor(CanvasToolName.TEXT, event=None, apply_cursor=True)
        == Qt.CursorShape.IBeamCursor
    )

    class DummyEvent:
        def buttons(self):
            return Qt.MouseButton.LeftButton

        def button(self):
            return Qt.MouseButton.LeftButton

    event = DummyEvent()
    assert (
        view_logic.get_cursor(
            CanvasToolName.ACTIVE_GRID_AREA, event=event, apply_cursor=True
        )
        == Qt.CursorShape.ClosedHandCursor
    )

    class DummyEvent2:
        def buttons(self):
            return Qt.MouseButton.NoButton

        def button(self):
            return Qt.MouseButton.NoButton

    event2 = DummyEvent2()
    assert (
        view_logic.get_cursor(
            CanvasToolName.ACTIVE_GRID_AREA, event=event2, apply_cursor=True
        )
        == Qt.CursorShape.OpenHandCursor
    )
    assert (
        view_logic.get_cursor(CanvasToolName.NONE, event=None, apply_cursor=True)
        == Qt.CursorShape.ArrowCursor
    )
    assert (
        view_logic.get_cursor(None, event=None, apply_cursor=True)
        == Qt.CursorShape.ArrowCursor
    )


def test_cursor_cache(logic):
    view_logic, _, _ = logic
    view_logic.cache_cursor(CanvasToolName.BRUSH, 32, "foo")
    assert view_logic.get_cached_cursor(CanvasToolName.BRUSH, 32) == "foo"
