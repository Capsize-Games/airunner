from typing import Dict, List, Optional
from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.art.data.outpaint_settings import OutpaintSettings
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

    def toggle_grid_snap(self, val):
        self.emit_signal(SignalCode.TOGGLE_GRID_SNAP, {"snap_to_grid": val})

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

    def upscale_x4(self, payload: Dict = {}):
        """
        Request an x4 upscale operation from the application layer.
        Emits SignalCode.UPSCALE_REQUEST so workers or managers can respond.
        """
        # Allow callers to pass an image and optional prompt. Keep a
        # backwards-compatible no-arg behavior that emits an empty dict.
        # Callers (e.g., UI widgets) should pass the current canvas image
        # when available so the worker can perform an immediate upscale.
        self.emit_signal(SignalCode.UPSCALE_REQUEST, payload)

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

    def layer_deleted(self, layer_id: int):
        self.emit_signal(
            SignalCode.LAYER_DELETED,
            {"layer_id": layer_id},
        )

    def layer_selection_changed(self, selected_layer_ids: List[int]):
        self.emit_signal(
            SignalCode.LAYER_SELECTION_CHANGED,
            {"selected_layer_ids": selected_layer_ids},
        )

    def update_grid_info(self, data: Dict):
        self.emit_signal(
            SignalCode.CANVAS_UPDATE_GRID_INFO,
            data,
        )

    def interrupt_image_generation(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def send_image_to_canvas(self, image_response: ImageResponse):
        self.cached_send_image_to_canvas = image_response
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

    def create_new_layer(self, **kwargs) -> CanvasLayer:
        self.begin_layer_operation("create")
        layer = CanvasLayer.objects.create(**kwargs)
        data = {"layer_id": layer.id}
        DrawingPadSettings.objects.create(**data)
        ControlnetSettings.objects.create(**data)
        ImageToImageSettings.objects.create(**data)
        OutpaintSettings.objects.create(**data)
        BrushSettings.objects.create(**data)
        MetadataSettings.objects.create(**data)
        if not layer:
            self.cancel_layer_operation("create")
            return
        self.commit_layer_operation("create", [layer.id])
        return layer

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
