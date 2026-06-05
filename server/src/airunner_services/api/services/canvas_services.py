"""Service-owned canvas API signal adapter."""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from airunner_services.api.api_service_base import APIServiceBase
from airunner_services.api.services._art_signal_code import get_art_signal_code
from airunner_services.database.models.brush_settings import BrushSettings
from airunner_services.database.models.canvas_layer import CanvasLayer
from airunner_services.database.models.controlnet_settings import (
    ControlnetSettings,
)
from airunner_services.database.models.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner_services.database.models.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner_services.database.models.metadata_settings import (
    MetadataSettings,
)
from airunner_services.database.models.outpaint_settings import (
    OutpaintSettings,
)
from airunner_services.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner_services.art.managers.stablediffusion.image_response import (
    ImageResponse,
)


def _point_coordinates(point: Any) -> tuple[int, int]:
    """Return x/y coordinates from one point-like object."""
    if hasattr(point, "x") and hasattr(point, "y"):
        return int(point.x()), int(point.y())
    if isinstance(point, (tuple, list)) and len(point) >= 2:
        return int(point[0]), int(point[1])
    raise TypeError("point must provide x/y coordinates")


class CanvasAPIService(APIServiceBase):
    """Route canvas actions through the shared signal bus."""

    def remove_background(self) -> None:
        self.emit_signal(get_art_signal_code("REMOVE_BACKGROUND"))

    def recenter_grid(self) -> None:
        self.emit_signal(get_art_signal_code("RECENTER_GRID_SIGNAL"))

    def toggle_grid(self, val) -> None:
        self.emit_signal(
            get_art_signal_code("TOGGLE_GRID"),
            {"show_grid": val},
        )

    def toggle_grid_snap(self, val) -> None:
        self.emit_signal(
            get_art_signal_code("TOGGLE_GRID_SNAP"),
            {"snap_to_grid": val},
        )

    def generate_mask(self) -> None:
        self.emit_signal(get_art_signal_code("GENERATE_MASK"))

    def mask_response(self, mask) -> None:
        self.emit_signal(
            get_art_signal_code("MASK_GENERATOR_WORKER_RESPONSE_SIGNAL"),
            {"mask": mask},
        )

    def image_updated(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_IMAGE_UPDATED_SIGNAL"))

    def update_current_layer(self, point: Any) -> None:
        x_pos, y_pos = _point_coordinates(point)
        self.emit_signal(
            get_art_signal_code("LAYER_UPDATE_CURRENT_SIGNAL"),
            {"pivot_point_x": x_pos, "pivot_point_y": y_pos},
        )

    def mask_updated(self) -> None:
        self.emit_signal(get_art_signal_code("MASK_UPDATED"))

    def brush_color_changed(self, color) -> None:
        self.emit_signal(
            get_art_signal_code("BRUSH_COLOR_CHANGED_SIGNAL"),
            {"color": color},
        )

    def image_from_path(self, path: str) -> None:
        self.emit_signal(
            get_art_signal_code("CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL"),
            {"image_path": path},
        )

    def new_document(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_CLEAR"), {})

    def undo(self) -> None:
        self.emit_signal(get_art_signal_code("UNDO_SIGNAL"))

    def redo(self) -> None:
        self.emit_signal(get_art_signal_code("REDO_SIGNAL"))

    def import_image(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_IMPORT_IMAGE_SIGNAL"))

    def export_image(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_EXPORT_IMAGE_SIGNAL"))

    def paste_image(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_PASTE_IMAGE_SIGNAL"))

    def copy_image(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_COPY_IMAGE_SIGNAL"))

    def cut_image(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_CUT_IMAGE_SIGNAL"))

    def rotate_image_90_clockwise(self) -> None:
        self.emit_signal(
            get_art_signal_code("CANVAS_ROTATE_90_CLOCKWISE_SIGNAL")
        )

    def rotate_image_90_counterclockwise(self) -> None:
        self.emit_signal(
            get_art_signal_code("CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL")
        )

    def mask_layer_toggled(self) -> None:
        self.emit_signal(get_art_signal_code("MASK_LAYER_TOGGLED"))

    def show_layers(self) -> None:
        self.emit_signal(get_art_signal_code("LAYERS_SHOW_SIGNAL"))

    def layer_opacity_changed(self, value) -> None:
        self.emit_signal(
            get_art_signal_code("LAYER_OPACITY_CHANGED_SIGNAL"),
            value,
        )

    def toggle_tool(self, tool, active) -> None:
        self.emit_signal(
            get_art_signal_code("TOGGLE_TOOL"),
            {"tool": tool, "active": active},
        )

    def tool_changed(self, tool, active) -> None:
        self.emit_signal(
            get_art_signal_code("APPLICATION_TOOL_CHANGED_SIGNAL"),
            {"tool": tool, "active": active},
        )

    def do_draw(self, force: bool = False) -> None:
        self.emit_signal(
            get_art_signal_code("SCENE_DO_DRAW_SIGNAL"),
            {"force_draw": force},
        )

    def clear_history(self) -> None:
        self.emit_signal(
            get_art_signal_code("HISTORY_UPDATED"),
            {"undo": 0, "redo": 0},
        )

    def update_history(self, undo: int, redo: int) -> None:
        self.emit_signal(
            get_art_signal_code("HISTORY_UPDATED"),
            {"undo": undo, "redo": redo},
        )

    def update_cursor(self, event, apply_cursor) -> None:
        self.emit_signal(
            get_art_signal_code("CANVAS_UPDATE_CURSOR"),
            {"event": event, "apply_cursor": apply_cursor},
        )

    def zoom_level_changed(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_ZOOM_LEVEL_CHANGED"))

    def layer_deleted(self, layer_id: int) -> None:
        self.emit_signal(
            get_art_signal_code("LAYER_DELETED"),
            {"layer_id": layer_id},
        )

    def layer_selection_changed(self, selected_layer_ids: List[int]) -> None:
        self.emit_signal(
            get_art_signal_code("LAYER_SELECTION_CHANGED"),
            {"selected_layer_ids": selected_layer_ids},
        )

    def update_grid_info(self, data: Dict) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_UPDATE_GRID_INFO"), data)

    def interrupt_image_generation(self) -> None:
        self.emit_signal(
            get_art_signal_code("INTERRUPT_IMAGE_GENERATION_SIGNAL")
        )

    def send_image_to_canvas(self, image_response: ImageResponse) -> None:
        self.cached_send_image_to_canvas = image_response
        self.emit_signal(
            get_art_signal_code("SEND_IMAGE_TO_CANVAS_SIGNAL"),
            {"image_response": image_response},
        )

    def input_image_changed(
        self,
        section: str,
        setting: str,
        value: Any,
        image_request: Optional[ImageRequest] = None,
    ) -> None:
        payload = {
            "section": section,
            "setting": setting,
            "value": value,
        }
        if image_request is not None:
            payload["image_request"] = image_request
        self.emit_signal(
            get_art_signal_code("INPUT_IMAGE_SETTINGS_CHANGED"),
            payload,
        )

    def update_image_positions(self) -> None:
        self.emit_signal(get_art_signal_code("CANVAS_UPDATE_IMAGE_POSITIONS"))

    def create_new_layer(self, **kwargs) -> Optional[CanvasLayer]:
        self.begin_layer_operation("create")
        layer = CanvasLayer.objects.create(**kwargs)
        if not layer:
            self.cancel_layer_operation("create")
            return None
        data = {"layer_id": layer.id}
        DrawingPadSettings.objects.create(**data)
        ControlnetSettings.objects.create(**data)
        ImageToImageSettings.objects.create(**data)
        OutpaintSettings.objects.create(**data)
        BrushSettings.objects.create(**data)
        MetadataSettings.objects.create(**data)
        self.commit_layer_operation("create", [layer.id])
        return layer

    def begin_layer_operation(
        self,
        action: str,
        layer_ids: Optional[list[int]] = None,
    ) -> None:
        self.emit_signal(
            get_art_signal_code("LAYER_OPERATION_BEGIN"),
            {"action": action, "layer_ids": layer_ids or []},
        )

    def commit_layer_operation(
        self,
        action: str,
        layer_ids: Optional[list[int]] = None,
    ) -> None:
        self.emit_signal(
            get_art_signal_code("LAYER_OPERATION_COMMIT"),
            {"action": action, "layer_ids": layer_ids or []},
        )

    def cancel_layer_operation(self, action: str) -> None:
        self.emit_signal(
            get_art_signal_code("LAYER_OPERATION_CANCEL"),
            {"action": action},
        )


__all__ = ["CanvasAPIService"]
