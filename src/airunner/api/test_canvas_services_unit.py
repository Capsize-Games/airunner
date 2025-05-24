"""
Unit tests for CanvasAPIService in canvas_services.py
"""

import pytest
from unittest.mock import MagicMock
from airunner.api.canvas_services import CanvasAPIService
from airunner.enums import SignalCode
from PySide6.QtCore import QPoint


@pytest.fixture
def service():
    # Patch emit_signal to track calls
    emit_signal = MagicMock()
    s = CanvasAPIService(emit_signal=emit_signal)
    return s


def test_recenter_grid(service):
    service.recenter_grid()
    service.emit_signal.assert_called_once_with(
        SignalCode.RECENTER_GRID_SIGNAL
    )


def test_toggle_grid(service):
    service.toggle_grid(True)
    service.emit_signal.assert_called_once_with(
        SignalCode.TOGGLE_GRID, {"show_grid": True}
    )


def test_generate_mask(service):
    service.generate_mask()
    service.emit_signal.assert_called_once_with(SignalCode.GENERATE_MASK)


def test_mask_response(service):
    mask = object()
    service.mask_response(mask)
    service.emit_signal.assert_called_once_with(
        SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL, {"mask": mask}
    )


def test_update_current_layer(service):
    point = QPoint(10, 20)
    service.update_current_layer(point)
    service.emit_signal.assert_called_once_with(
        SignalCode.LAYER_UPDATE_CURRENT_SIGNAL,
        {"pivot_point_x": 10, "pivot_point_y": 20},
    )


def test_layer_opacity_changed(service):
    service.layer_opacity_changed(0.5)
    service.emit_signal.assert_called_once_with(
        SignalCode.LAYER_OPACITY_CHANGED_SIGNAL, 0.5
    )


def test_toggle_tool(service):
    service.toggle_tool("brush", True)
    service.emit_signal.assert_called_once_with(
        SignalCode.TOGGLE_TOOL, {"tool": "brush", "active": True}
    )


def test_tool_changed(service):
    service.tool_changed("eraser", False)
    service.emit_signal.assert_called_once_with(
        SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL,
        {"tool": "eraser", "active": False},
    )


def test_do_draw(service):
    service.do_draw(force=True)
    service.emit_signal.assert_called_once_with(
        SignalCode.SCENE_DO_DRAW_SIGNAL, {"force_draw": True}
    )


def test_clear_history(service):
    service.clear_history()
    service.emit_signal.assert_called_once_with(
        SignalCode.HISTORY_UPDATED, {"undo": 0, "redo": 0}
    )


def test_update_history(service):
    service.update_history(2, 3)
    service.emit_signal.assert_called_once_with(
        SignalCode.HISTORY_UPDATED, {"undo": 2, "redo": 3}
    )


def test_update_cursor(service):
    service.update_cursor("move", True)
    service.emit_signal.assert_called_once_with(
        SignalCode.CANVAS_UPDATE_CURSOR,
        {"event": "move", "apply_cursor": True},
    )


def test_send_image_to_canvas(service):
    image_response = object()
    service.send_image_to_canvas(image_response)
    service.emit_signal.assert_called_once_with(
        SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
        {"image_response": image_response},
    )


def test_input_image_changed(service):
    service.input_image_changed("section", "setting", 42)
    service.emit_signal.assert_called_once_with(
        SignalCode.INPUT_IMAGE_SETTINGS_CHANGED,
        {"section": "section", "setting": "setting", "value": 42},
    )


def test_update_image_positions(service):
    service.update_image_positions()
    service.emit_signal.assert_called_once_with(
        SignalCode.CANVAS_UPDATE_IMAGE_POSITIONS
    )


def test_paste_image(service):
    service.paste_image()
    service.emit_signal.assert_called_once_with(
        SignalCode.CANVAS_PASTE_IMAGE_SIGNAL
    )


def test_copy_image(service):
    service.copy_image()
    service.emit_signal.assert_called_once_with(
        SignalCode.CANVAS_COPY_IMAGE_SIGNAL
    )


def test_cut_image(service):
    service.cut_image()
    service.emit_signal.assert_called_once_with(
        SignalCode.CANVAS_CUT_IMAGE_SIGNAL
    )


def test_rotate_image_90_clockwise(service):
    service.rotate_image_90_clockwise()
    service.emit_signal.assert_called_once_with(
        SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL
    )


def test_rotate_image_90_counterclockwise(service):
    service.rotate_image_90_counterclockwise()
    service.emit_signal.assert_called_once_with(
        SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL
    )


def test_mask_layer_toggled(service):
    service.mask_layer_toggled()
    service.emit_signal.assert_called_once_with(SignalCode.MASK_LAYER_TOGGLED)


def test_show_layers(service):
    service.show_layers()
    service.emit_signal.assert_called_once_with(SignalCode.LAYERS_SHOW_SIGNAL)


def test_zoom_level_changed(service):
    service.zoom_level_changed()
    service.emit_signal.assert_called_once_with(
        SignalCode.CANVAS_ZOOM_LEVEL_CHANGED
    )


def test_interrupt_image_generation(service):
    service.interrupt_image_generation()
    service.emit_signal.assert_called_once_with(
        SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL
    )
