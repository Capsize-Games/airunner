from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode
from PySide6.QtCore import QPoint
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)


class CanvasAPIService(APIServiceBase):
    def recenter_grid(self):
        self.emit_signal(SignalCode.RECENTER_GRID_SIGNAL)

    def toggle_grid(self, val):
        self.emit_signal(SignalCode.TOGGLE_GRID, {"show_grid": val})

    def generate_mask(self):
        self.emit_signal(SignalCode.GENERATE_MASK)

    def mask_response(self, mask):
        self.emit_signal(
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL, {"mask": mask}
        )

    def image_updated(self):
        self.emit_signal(SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL)

    def update_current_layer(self, point: QPoint):
        self.emit_signal(
            SignalCode.LAYER_UPDATE_CURRENT_SIGNAL,
            {"pivot_point_x": point.x(), "pivot_point_y": point.y()},
        )

    def mask_updated(self):
        self.emit_signal(SignalCode.MASK_UPDATED)

    def brush_color_changed(self, color):
        self.emit_signal(
            SignalCode.BRUSH_COLOR_CHANGED_SIGNAL, {"color": color}
        )

    def image_from_path(self, path):
        self.emit_signal(
            SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL, {"image_path": path}
        )

    def clear(self):
        self.emit_signal(SignalCode.CANVAS_CLEAR, {})

    def undo(self):
        self.emit_signal(SignalCode.UNDO_SIGNAL)

    def redo(self):
        self.emit_signal(SignalCode.REDO_SIGNAL)

    def import_image(self):
        self.emit_signal(SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL)

    def export_image(self):
        self.emit_signal(SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL)

    def paste_image(self):
        self.emit_signal(SignalCode.CANVAS_PASTE_IMAGE_SIGNAL)

    def copy_image(self):
        self.emit_signal(SignalCode.CANVAS_COPY_IMAGE_SIGNAL)

    def cut_image(self):
        self.emit_signal(SignalCode.CANVAS_CUT_IMAGE_SIGNAL)

    def rotate_image_90_clockwise(self):
        self.emit_signal(SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL)

    def rotate_image_90_counterclockwise(self):
        self.emit_signal(SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL)

    def mask_layer_toggled(self):
        self.emit_signal(SignalCode.MASK_LAYER_TOGGLED)

    def show_layers(self):
        self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)

    def layer_opacity_changed(self, value):
        self.emit_signal(SignalCode.LAYER_OPACITY_CHANGED_SIGNAL, value)

    def toggle_tool(self, tool, active):
        self.emit_signal(
            SignalCode.TOGGLE_TOOL, {"tool": tool, "active": active}
        )

    def tool_changed(self, tool, active):
        self.emit_signal(
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL,
            {"tool": tool, "active": active},
        )

    def do_draw(self, force=False):
        self.emit_signal(
            SignalCode.SCENE_DO_DRAW_SIGNAL, {"force_draw": force}
        )

    def clear_history(self):
        self.emit_signal(SignalCode.HISTORY_UPDATED, {"undo": 0, "redo": 0})

    def update_history(self, undo, redo):
        self.emit_signal(
            SignalCode.HISTORY_UPDATED, {"undo": undo, "redo": redo}
        )

    def update_cursor(self, event, apply_cursor):
        self.emit_signal(
            SignalCode.CANVAS_UPDATE_CURSOR,
            {"event": event, "apply_cursor": apply_cursor},
        )

    def zoom_level_changed(self):
        self.emit_signal(SignalCode.CANVAS_ZOOM_LEVEL_CHANGED)

    def interrupt_image_generation(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def send_image_to_canvas(self, image_response: ImageResponse):
        self.emit_signal(
            SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
            {"image_response": image_response},
        )

    def input_image_changed(self, section, setting, value):
        self.emit_signal(
            SignalCode.INPUT_IMAGE_SETTINGS_CHANGED,
            {"section": section, "setting": setting, "value": value},
        )

    def update_image_positions(self):
        self.emit_signal(SignalCode.CANVAS_UPDATE_IMAGE_POSITIONS)

    def begin_layer_operation(
        self, action: str, layer_ids: list[int] | None = None
    ):
        self.emit_signal(
            SignalCode.LAYER_OPERATION_BEGIN,
            {"action": action, "layer_ids": layer_ids or []},
        )

    def commit_layer_operation(
        self, action: str, layer_ids: list[int] | None = None
    ):
        self.emit_signal(
            SignalCode.LAYER_OPERATION_COMMIT,
            {"action": action, "layer_ids": layer_ids or []},
        )

    def cancel_layer_operation(self, action: str):
        self.emit_signal(
            SignalCode.LAYER_OPERATION_CANCEL,
            {"action": action},
        )
