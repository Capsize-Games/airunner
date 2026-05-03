"""Tests for canvas footer status text updates."""

from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

from airunner.components.art.gui.widgets.canvas.canvas_widget import (
    CanvasWidget,
)
from airunner.enums import CanvasToolName


def test_update_grid_info_shows_active_grid_coordinates():
    """The footer should show active-grid coordinates on the right."""
    widget = CanvasWidget.__new__(CanvasWidget)
    widget.ui = SimpleNamespace(
        grid_info=Mock(),
        active_item_info=Mock(),
    )
    widget._offset_x = 0
    widget._offset_y = 0

    with patch.object(
        CanvasWidget,
        "current_tool",
        new_callable=PropertyMock,
        return_value=CanvasToolName.ACTIVE_GRID_AREA,
    ), patch.object(
        CanvasWidget,
        "grid_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(zoom_level=1.25),
    ), patch.object(
        CanvasWidget,
        "active_grid_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(pos_x=144, pos_y=44),
    ), patch.object(
        CanvasWidget,
        "drawing_pad_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(x_pos=0, y_pos=0),
    ):
        CanvasWidget.update_grid_info(
            widget,
            {"offset_x": 10, "offset_y": -20},
        )

    widget.ui.grid_info.setText.assert_called_once_with(
        "10, -20, 125.0%"
    )
    widget.ui.active_item_info.setText.assert_called_once_with(
        "Grid: 144, 44"
    )


def test_update_grid_info_shows_active_layer_coordinates():
    """The footer should show active-layer coordinates for move mode."""
    widget = CanvasWidget.__new__(CanvasWidget)
    widget.ui = SimpleNamespace(
        grid_info=Mock(),
        active_item_info=Mock(),
    )
    widget._offset_x = 0
    widget._offset_y = 0

    with patch.object(
        CanvasWidget,
        "current_tool",
        new_callable=PropertyMock,
        return_value=CanvasToolName.MOVE,
    ), patch.object(
        CanvasWidget,
        "grid_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(zoom_level=1.0),
    ), patch.object(
        CanvasWidget,
        "active_grid_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(pos_x=0, pos_y=0),
    ), patch.object(
        CanvasWidget,
        "drawing_pad_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(x_pos=321, y_pos=654),
    ):
        CanvasWidget.update_grid_info(
            widget,
            {"offset_x": 0, "offset_y": 0},
        )

    widget.ui.grid_info.setText.assert_called_once_with("0, 0, 100.0%")
    widget.ui.active_item_info.setText.assert_called_once_with(
        "Layer: 321, 654"
    )


def test_update_grid_info_clears_active_item_text_for_other_tools():
    """Non-move tools should not show a right-side position readout."""
    widget = CanvasWidget.__new__(CanvasWidget)
    widget.ui = SimpleNamespace(
        grid_info=Mock(),
        active_item_info=Mock(),
    )
    widget._offset_x = 0
    widget._offset_y = 0

    with patch.object(
        CanvasWidget,
        "current_tool",
        new_callable=PropertyMock,
        return_value=CanvasToolName.BRUSH,
    ), patch.object(
        CanvasWidget,
        "grid_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(zoom_level=1.0),
    ), patch.object(
        CanvasWidget,
        "active_grid_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(pos_x=144, pos_y=44),
    ), patch.object(
        CanvasWidget,
        "drawing_pad_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(x_pos=321, y_pos=654),
    ):
        CanvasWidget.update_grid_info(
            widget,
            {"offset_x": 1, "offset_y": 2},
        )

    widget.ui.active_item_info.setText.assert_called_once_with("")