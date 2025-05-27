import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QPoint
from airunner.gui.widgets.canvas.logic.canvas_logic import CanvasLogic
from airunner.enums import CanvasToolName


class DummySettings:
    def __init__(self):
        self.current_tool = None
        self.pivot_point_x = 0
        self.pivot_point_y = 0


@pytest.fixture
def logic():
    settings = DummySettings()
    updates = []

    def update_application_settings(key, value):
        updates.append((key, value))
        setattr(settings, key, value)

    return (
        CanvasLogic(settings, update_application_settings),
        settings,
        updates,
    )


def test_current_tool_none(logic):
    canvas_logic, settings, _ = logic
    settings.current_tool = None
    assert canvas_logic.current_tool is None


def test_current_tool_valid(logic):
    canvas_logic, settings, _ = logic
    settings.current_tool = "brush"
    assert canvas_logic.current_tool == CanvasToolName.BRUSH


def test_current_tool_invalid(logic):
    canvas_logic, settings, _ = logic
    settings.current_tool = "not_a_tool"
    assert canvas_logic.current_tool is None


def test_image_pivot_point_getter_setter(logic):
    canvas_logic, settings, updates = logic
    settings.pivot_point_x = 5
    settings.pivot_point_y = 7
    pt = canvas_logic.image_pivot_point
    assert isinstance(pt, QPoint)
    assert pt.x() == 5 and pt.y() == 7
    # Test setter
    canvas_logic.image_pivot_point = QPoint(11, 13)
    assert settings.pivot_point_x == 11
    assert settings.pivot_point_y == 13
    assert ("pivot_point_x", 11) in updates
    assert ("pivot_point_y", 13) in updates


def test_update_action_buttons_sets_checked_and_blocks_signals():
    from airunner.enums import CanvasToolName

    logic = CanvasLogic(
        application_settings=object(),
        update_application_settings=lambda k, v: None,
    )
    ui = MagicMock()
    for btn in [
        "active_grid_area_button",
        "brush_button",
        "eraser_button",
        "text_button",
        "grid_button",
    ]:
        setattr(ui, btn, MagicMock())
    grid_settings = MagicMock()
    grid_settings.show_grid = True
    logic.update_action_buttons(ui, grid_settings, CanvasToolName.BRUSH, True)
    ui.active_grid_area_button.setChecked.assert_called()
    ui.brush_button.setChecked.assert_called_with(True)
    ui.eraser_button.setChecked.assert_called()
    ui.text_button.setChecked.assert_called()
    ui.grid_button.setChecked.assert_called_with(True)
    # Ensure blockSignals called
    for btn in [
        "active_grid_area_button",
        "brush_button",
        "eraser_button",
        "text_button",
        "grid_button",
    ]:
        getattr(ui, btn).blockSignals.assert_any_call(True)
        getattr(ui, btn).blockSignals.assert_any_call(False)


def test_get_cursor_type_brush_and_eraser():
    logic = CanvasLogic(
        application_settings=object(),
        update_application_settings=lambda k, v: None,
    )
    assert (
        logic.get_cursor_type(
            CanvasToolName.BRUSH, event=None, brush_size=20, apply_cursor=True
        )
        == "circle_brush"
    )
    assert (
        logic.get_cursor_type(
            CanvasToolName.ERASER, event=None, brush_size=20, apply_cursor=True
        )
        == "circle_brush"
    )
    assert (
        logic.get_cursor_type(
            CanvasToolName.BRUSH, event=None, brush_size=20, apply_cursor=False
        )
        == "arrow"
    )


def test_get_cursor_type_active_grid_area():
    logic = CanvasLogic(
        application_settings=object(),
        update_application_settings=lambda k, v: None,
    )

    class DummyEvent:
        def buttons(self):
            return 1  # Simulate Qt.MouseButton.LeftButton

        def button(self):
            return 1

    event = DummyEvent()
    assert (
        logic.get_cursor_type(
            CanvasToolName.ACTIVE_GRID_AREA, event=event, apply_cursor=True
        )
        == "closed_hand"
    )

    class DummyEvent2:
        def buttons(self):
            return 0  # Simulate Qt.MouseButton.NoButton

        def button(self):
            return 0

    event2 = DummyEvent2()
    assert (
        logic.get_cursor_type(
            CanvasToolName.ACTIVE_GRID_AREA, event=event2, apply_cursor=True
        )
        == "open_hand"
    )


def test_get_cursor_type_none_and_default():
    logic = CanvasLogic(
        application_settings=object(),
        update_application_settings=lambda k, v: None,
    )
    assert (
        logic.get_cursor_type(CanvasToolName.NONE, event=None, apply_cursor=True)
        == "arrow"
    )
    assert logic.get_cursor_type(None, event=None, apply_cursor=True) == "arrow"
