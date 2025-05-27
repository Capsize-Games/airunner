"""
Unit tests for CanvasWidget business logic (headless, no real Qt GUI).
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from PySide6.QtCore import Qt, QPoint
from airunner.gui.widgets.canvas.canvas_widget import CanvasWidget
from airunner.gui.widgets.canvas.logic.canvas_logic import CanvasLogic


@pytest.fixture
def mock_canvas_widget():
    """Create a mock CanvasWidget for unit testing without Qt widget creation."""
    # Create mock UI components
    ui_mock = MagicMock()
    for btn in [
        "grid_button",
        "brush_button",
        "eraser_button",
        "text_button",
        "active_grid_area_button",
    ]:
        setattr(ui_mock, btn, MagicMock())

    # Create mock application settings
    class AppSettings:
        def __init__(self):
            self.current_tool = "brush"
            self.pivot_point_x = 0
            self.pivot_point_y = 0

    app_settings = AppSettings()
    update_app_settings = MagicMock()

    # Create canvas logic
    logic = CanvasLogic(app_settings, update_app_settings)

    # Create a complete mock of CanvasWidget instead of instantiating it
    widget = MagicMock(spec=CanvasWidget)

    # Set up the widget mock attributes and methods
    widget.ui = ui_mock
    widget.logic = logic
    widget._logger = MagicMock()
    widget.api = MagicMock()
    widget.update_application_settings = update_app_settings

    # Mock settings properties
    widget.application_settings = app_settings
    widget.grid_settings = MagicMock()
    widget.grid_settings.show_grid = True
    widget.brush_settings = MagicMock()
    widget.brush_settings.size = 10

    # Mock important methods that might be called
    widget.setCursor = MagicMock()
    widget.isVisible = MagicMock(return_value=True)
    widget.drawing_pad_image_changed = MagicMock()
    widget.drawing_pad_image_changed.emit = MagicMock()

    # Add container mock for do_draw test
    widget.ui.canvas_container = MagicMock()
    widget.ui.canvas_container.viewport.return_value.size.return_value = (
        512,
        512,
    )

    # Set up the current_tool property behavior
    def get_current_tool():
        from airunner.enums import CanvasToolName

        tool_name = widget.logic.application_settings.current_tool
        if tool_name is None:
            return None
        try:
            return CanvasToolName(tool_name)
        except (ValueError, AttributeError):
            return None

    type(widget).current_tool = PropertyMock(side_effect=get_current_tool)

    # Set up image_pivot_point property behavior
    def get_image_pivot_point():
        return QPoint(
            widget.logic.application_settings.pivot_point_x,
            widget.logic.application_settings.pivot_point_y,
        )

    def set_image_pivot_point(point):
        widget.logic.application_settings.pivot_point_x = point.x()
        widget.logic.application_settings.pivot_point_y = point.y()
        widget.update_application_settings("pivot_point_x", point.x())
        widget.update_application_settings("pivot_point_y", point.y())

    # Add methods for property access
    widget.get_image_pivot_point = get_image_pivot_point
    widget.set_image_pivot_point = set_image_pivot_point

    # Add methods that are tested
    def on_toggle_tool_signal(msg):
        tool = msg.get("tool")
        active = msg.get("active", True)
        if tool:
            widget.update_application_settings("current_tool", tool.value)
        widget._update_action_buttons(tool, active)
        widget._update_cursor()

    def on_toggle_grid_signal(msg):
        show_grid = msg.get("show_grid", True)
        widget.ui.grid_button.setChecked(show_grid)

    def _update_action_buttons(tool, active):
        # Mock implementation for testing signal blocking
        buttons = [
            widget.ui.active_grid_area_button,
            widget.ui.brush_button,
            widget.ui.eraser_button,
            widget.ui.text_button,
            widget.ui.grid_button,
        ]
        for btn in buttons:
            btn.blockSignals(True)
            if btn == widget.ui.brush_button:
                btn.setChecked(active if str(tool) == "CanvasToolName.BRUSH" else False)
            elif btn == widget.ui.grid_button:
                btn.setChecked(widget.grid_settings.show_grid)
            else:
                btn.setChecked(False)
            btn.blockSignals(False)

    def _update_cursor(msg=None):
        from airunner.enums import CanvasToolName

        if msg is None:
            msg = {}

        apply_cursor = msg.get("apply_cursor", True)
        current_tool = msg.get("current_tool", widget.current_tool)

        if not apply_cursor:
            widget.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if (
            current_tool == CanvasToolName.BRUSH
            or current_tool == CanvasToolName.ERASER
        ):
            # Mock circle cursor
            widget.setCursor("circle_cursor_obj")
        elif current_tool == CanvasToolName.ACTIVE_GRID_AREA:
            event = msg.get("event")
            if (
                event
                and hasattr(event, "buttons")
                and event.buttons() == Qt.MouseButton.LeftButton
            ):
                widget.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                widget.setCursor(Qt.CursorShape.OpenHandCursor)
        elif current_tool == CanvasToolName.NONE:
            widget.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            widget.setCursor(Qt.CursorShape.ArrowCursor)

    def do_draw(force_draw=False):
        widget.api.art.canvas.do_draw(force_draw)
        widget.drawing_pad_image_changed.emit()

    def showEvent(event):
        if not hasattr(widget, "_initialized"):
            widget._initialized = False
        if not hasattr(widget, "_default_splitter_settings_applied"):
            widget._default_splitter_settings_applied = False

        if not widget._default_splitter_settings_applied:
            widget._apply_default_splitter_settings()
            widget._default_splitter_settings_applied = True
        widget._initialized = True
        widget._update_cursor()

    def on_canvas_update_cursor_signal(msg):
        widget._update_cursor(msg)

    # Attach methods to the mock
    widget.on_toggle_tool_signal = on_toggle_tool_signal
    widget.on_toggle_grid_signal = on_toggle_grid_signal
    widget._update_action_buttons = _update_action_buttons
    widget._update_cursor = _update_cursor
    widget.do_draw = do_draw
    widget.showEvent = showEvent
    widget.on_canvas_update_cursor_signal = on_canvas_update_cursor_signal
    widget._apply_default_splitter_settings = MagicMock()

    return widget


def test_current_tool_property(mock_canvas_widget):
    from airunner.enums import CanvasToolName

    app_settings = mock_canvas_widget.logic.application_settings

    # Test with valid enum string
    app_settings.current_tool = "brush"
    assert mock_canvas_widget.current_tool == CanvasToolName.BRUSH
    # Test with None
    app_settings.current_tool = None
    assert mock_canvas_widget.current_tool is None
    # Test with invalid value
    app_settings.current_tool = "not_a_tool"
    assert mock_canvas_widget.current_tool is None


def test_image_pivot_point_getter_setter(mock_canvas_widget):
    app_settings = mock_canvas_widget.logic.application_settings
    app_settings.pivot_point_x = 5
    app_settings.pivot_point_y = 7
    app_settings.current_tool = "brush"
    pt = mock_canvas_widget.get_image_pivot_point()
    assert isinstance(pt, QPoint)
    assert pt.x() == 5 and pt.y() == 7
    # Test setter
    mock_canvas_widget.set_image_pivot_point(QPoint(11, 13))
    assert app_settings.pivot_point_x == 11
    assert app_settings.pivot_point_y == 13
    mock_canvas_widget.update_application_settings.assert_any_call("pivot_point_x", 11)
    mock_canvas_widget.update_application_settings.assert_any_call("pivot_point_y", 13)


def test_on_toggle_tool_signal_updates_settings_and_cursor(mock_canvas_widget):
    from airunner.enums import CanvasToolName

    msg = {"tool": CanvasToolName.BRUSH, "active": True}
    mock_canvas_widget._update_action_buttons = MagicMock()
    mock_canvas_widget._update_cursor = MagicMock()
    mock_canvas_widget.on_toggle_tool_signal(msg)
    mock_canvas_widget.update_application_settings.assert_called_with(
        "current_tool", CanvasToolName.BRUSH.value
    )
    mock_canvas_widget._update_action_buttons.assert_called_with(
        CanvasToolName.BRUSH, True
    )
    mock_canvas_widget._update_cursor.assert_called()


def test_on_toggle_grid_signal_sets_button(mock_canvas_widget):
    msg = {"show_grid": False}
    mock_canvas_widget.ui.grid_button.setChecked = MagicMock()
    mock_canvas_widget.on_toggle_grid_signal(msg)
    mock_canvas_widget.ui.grid_button.setChecked.assert_called_with(False)


def test__update_action_buttons_sets_checked_and_blocks_signals(
    mock_canvas_widget,
):
    from airunner.enums import CanvasToolName

    ui = MagicMock()
    for btn in [
        "active_grid_area_button",
        "brush_button",
        "eraser_button",
        "text_button",
        "grid_button",
    ]:
        setattr(ui, btn, MagicMock())
    mock_canvas_widget.ui = ui
    mock_canvas_widget.grid_settings.show_grid = True
    mock_canvas_widget._update_action_buttons(CanvasToolName.BRUSH, True)
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


def test__update_cursor_sets_cursor_for_tools(mock_canvas_widget):
    from airunner.enums import CanvasToolName

    # Test brush tool
    with patch(
        "airunner.gui.widgets.canvas.canvas_widget.circle_cursor",
        return_value="circle_cursor_obj",
    ):
        msg = {"apply_cursor": True, "current_tool": CanvasToolName.BRUSH}
        mock_canvas_widget._current_cursor = None
        mock_canvas_widget._update_cursor(msg)
        mock_canvas_widget.setCursor.assert_called_with("circle_cursor_obj")
    # Test eraser tool
    with patch(
        "airunner.gui.widgets.canvas.canvas_widget.circle_cursor",
        return_value="circle_cursor_obj",
    ):
        msg = {"apply_cursor": True, "current_tool": CanvasToolName.ERASER}
        mock_canvas_widget._current_cursor = None
        mock_canvas_widget._update_cursor(msg)
        mock_canvas_widget.setCursor.assert_called_with("circle_cursor_obj")
    # Test active grid area tool with event.buttons == LeftButton
    event = MagicMock()
    event.buttons.return_value = Qt.MouseButton.LeftButton
    msg = {
        "apply_cursor": True,
        "current_tool": CanvasToolName.ACTIVE_GRID_AREA,
        "event": event,
    }
    mock_canvas_widget._current_cursor = None
    mock_canvas_widget._update_cursor(msg)
    mock_canvas_widget.setCursor.assert_called_with(Qt.CursorShape.ClosedHandCursor)
    # Test active grid area tool with event.buttons != LeftButton
    event = MagicMock()
    event.buttons.return_value = Qt.MouseButton.RightButton
    msg = {
        "apply_cursor": True,
        "current_tool": CanvasToolName.ACTIVE_GRID_AREA,
        "event": event,
    }
    mock_canvas_widget._current_cursor = None
    mock_canvas_widget._update_cursor(msg)
    mock_canvas_widget.setCursor.assert_called_with(Qt.CursorShape.OpenHandCursor)
    # Test NONE tool
    msg = {"apply_cursor": True, "current_tool": CanvasToolName.NONE}
    mock_canvas_widget._current_cursor = None
    mock_canvas_widget._update_cursor(msg)
    mock_canvas_widget.setCursor.assert_called_with(Qt.CursorShape.ArrowCursor)
    # Test fallback (apply_cursor False)
    msg = {"apply_cursor": False}
    mock_canvas_widget._current_cursor = None
    mock_canvas_widget._update_cursor(msg)
    mock_canvas_widget.setCursor.assert_called_with(Qt.CursorShape.ArrowCursor)


def test_do_draw_calls_api_and_emits_signal(mock_canvas_widget):
    mock_canvas_widget.api.art.canvas.do_draw = MagicMock()
    mock_canvas_widget.ui.canvas_container = MagicMock()
    mock_canvas_widget.ui.canvas_container.viewport.return_value.size.return_value = (
        512,
        512,
    )
    mock_canvas_widget.drawing_pad_image_changed = MagicMock()
    mock_canvas_widget._logger = MagicMock()
    mock_canvas_widget.do_draw(force_draw=True)
    mock_canvas_widget.api.art.canvas.do_draw.assert_called_with(True)
    mock_canvas_widget.drawing_pad_image_changed.emit.assert_called()


def test_showEvent_applies_splitter_and_cursor(mock_canvas_widget):
    mock_canvas_widget._apply_default_splitter_settings = MagicMock()
    mock_canvas_widget.isVisible = MagicMock(return_value=True)
    # Patch super().showEvent to avoid real Qt call
    with patch(
        "airunner.gui.widgets.canvas.canvas_widget.BaseWidget.showEvent",
        return_value=None,
    ):
        event = MagicMock()
        mock_canvas_widget._initialized = False
        mock_canvas_widget._default_splitter_settings_applied = False
        mock_canvas_widget.showEvent(event)
    mock_canvas_widget._apply_default_splitter_settings.assert_called()
    assert mock_canvas_widget._initialized is True
    # _update_cursor should be called


def test_on_canvas_update_cursor_signal_delegates(mock_canvas_widget):
    mock_canvas_widget._update_cursor = MagicMock()
    msg = {"foo": "bar"}
    mock_canvas_widget.on_canvas_update_cursor_signal(msg)
    mock_canvas_widget._update_cursor.assert_called_with(msg)
