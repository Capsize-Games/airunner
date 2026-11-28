"""Service-owned canvas API signal adapter."""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from airunner_services.api.api_service_base import APIServiceBase
from airunner_services.api.services._art_signal_code import get_art_signal_code
from airunner_services.database.models.canvas_layer import CanvasLayer
from airunner_services.database.models.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner_services.database.models.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner_services.database.models.outpaint_settings import (
    OutpaintSettings,
)
from airunner_services.art.managers.stablediffusion.image_request import ImageRequest
from airunner_services.art.managers.stablediffusion.image_response import ImageResponse


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
        """Emit the remove background signal."""
        self.emit_signal(get_art_signal_code("REMOVE_BACKGROUND"))

    def recenter_grid(self) -> None:
        """Emit the recenter grid signal."""
        self.emit_signal(get_art_signal_code("RECENTER_GRID_SIGNAL"))

    def toggle_grid(self, val) -> None:
        """Emit the toggle grid signal."""
        self.emit_signal(
            get_art_signal_code("TOGGLE_GRID"),
            {"show_grid": val},
        )

    def toggle_grid_snap(self, val) -> None:
        """Emit the toggle grid snap signal."""
        self.emit_signal(
            get_art_signal_code("TOGGLE_GRID_SNAP"),
            {"snap_to_grid": val},
        )

    def generate_mask(self) -> None:
        """Emit the generate mask signal."""
        self.emit_signal(get_art_signal_code("GENERATE_MASK"))

    def mask_response(self, mask) -> None:
        """Emit the mask generator response signal."""
        self.emit_signal(
            get_art_signal_code("MASK_GENERATOR_WORKER_RESPONSE_SIGNAL"),
            {"mask": mask},
        )

    def image_updated(self) -> None:
        """Emit the canvas image updated signal."""
        self.emit_signal(get_art_signal_code("CANVAS_IMAGE_UPDATED_SIGNAL"))

    def update_current_layer(self, point: Any) -> None:
        """Emit the layer update current signal for one point."""
        x_pos, y_pos = _point_coordinates(point)
        self.emit_signal(
            get_art_signal_code("LAYER_UPDATE_CURRENT_SIGNAL"),
            {"pivot_point_x": x_pos, "pivot_point_y": y_pos},
        )

    def mask_updated(self) -> None:
        """Emit the mask updated signal."""
        self.emit_signal(get_art_signal_code("MASK_UPDATED"))

    def brush_color_changed(self, color) -> None:
        """Emit the brush color changed signal."""
        self.emit_signal(
            get_art_signal_code("BRUSH_COLOR_CHANGED_SIGNAL"),
            {"color": color},
        )

    def image_from_path(self, path: str) -> None:
        """Emit the canvas load image from path signal."""
        self.emit_signal(
            get_art_signal_code("CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL"),
            {"image_path": path},
        )

    def new_document(self) -> None:
        """Start a new canvas document."""
        self.clear()

    def clear(self) -> None:
        """Emit the canvas clear signal."""
        self.emit_signal(get_art_signal_code("CANVAS_CLEAR"), {})

    def undo(self) -> None:
        """Emit the undo signal."""
        self.emit_signal(get_art_signal_code("UNDO_SIGNAL"))

    def redo(self) -> None:
        """Emit the redo signal."""
        self.emit_signal(get_art_signal_code("REDO_SIGNAL"))

    def import_image(self) -> None:
        """Emit the canvas import image signal."""
        self.emit_signal(get_art_signal_code("CANVAS_IMPORT_IMAGE_SIGNAL"))

    def export_image(self) -> None:
        """Emit the canvas export image signal."""
        self.emit_signal(get_art_signal_code("CANVAS_EXPORT_IMAGE_SIGNAL"))

    def paste_image(self) -> None:
        """Emit the canvas paste image signal."""
        self.emit_signal(get_art_signal_code("CANVAS_PASTE_IMAGE_SIGNAL"))

    def copy_image(self) -> None:
        """Emit the canvas copy image signal."""
        self.emit_signal(get_art_signal_code("CANVAS_COPY_IMAGE_SIGNAL"))

    def cut_image(self) -> None:
        """Emit the canvas cut image signal."""
        self.emit_signal(get_art_signal_code("CANVAS_CUT_IMAGE_SIGNAL"))

    def rotate_image_90_clockwise(self) -> None:
        """Emit the rotate 90 clockwise signal."""
        self.emit_signal(
            get_art_signal_code("CANVAS_ROTATE_90_CLOCKWISE_SIGNAL")
        )

    def rotate_image_90_counterclockwise(self) -> None:
        """Emit the rotate 90 counterclockwise signal."""
        self.emit_signal(
            get_art_signal_code("CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL")
        )

    def mask_layer_toggled(self) -> None:
        """Emit the mask layer toggled signal."""
        self.emit_signal(get_art_signal_code("MASK_LAYER_TOGGLED"))

    def show_layers(self) -> None:
        """Emit the layers show signal."""
        self.emit_signal(get_art_signal_code("LAYERS_SHOW_SIGNAL"))

    def layer_opacity_changed(self, value) -> None:
        """Emit the layer opacity changed signal."""
        self.emit_signal(
            get_art_signal_code("LAYER_OPACITY_CHANGED_SIGNAL"),
            value,
        )

    def toggle_tool(self, tool, active) -> None:
        """Emit the toggle tool signal."""
        self.emit_signal(
            get_art_signal_code("TOGGLE_TOOL"),
            {"tool": tool, "active": active},
        )

    def tool_changed(self, tool, active) -> None:
        """Emit the application tool changed signal."""
        self.emit_signal(
            get_art_signal_code("APPLICATION_TOOL_CHANGED_SIGNAL"),
            {"tool": tool, "active": active},
        )

    def do_draw(self, force: bool = False) -> None:
        """Emit the scene do draw signal."""
        self.emit_signal(
            get_art_signal_code("SCENE_DO_DRAW_SIGNAL"),
            {"force_draw": force},
        )

    def clear_history(self) -> None:
        """Emit the history updated signal with empty history."""
        self.emit_signal(
            get_art_signal_code("HISTORY_UPDATED"),
            {"undo": 0, "redo": 0},
        )

    def update_history(self, undo: int, redo: int) -> None:
        """Emit the history updated signal."""
        self.emit_signal(
            get_art_signal_code("HISTORY_UPDATED"),
            {"undo": undo, "redo": redo},
        )

    def update_cursor(self, event, apply_cursor) -> None:
        """Emit the canvas update cursor signal."""
        self.emit_signal(
            get_art_signal_code("CANVAS_UPDATE_CURSOR"),
            {"event": event, "apply_cursor": apply_cursor},
        )

    def zoom_level_changed(self) -> None:
        """Emit the canvas zoom level changed signal."""
        self.emit_signal(get_art_signal_code("CANVAS_ZOOM_LEVEL_CHANGED"))

    def layer_deleted(self, layer_id: int) -> None:
        """Emit the layer deleted signal."""
        self.emit_signal(
            get_art_signal_code("LAYER_DELETED"),
            {"layer_id": layer_id},
        )

    def layer_selection_changed(self, selected_layer_ids: List[int]) -> None:
        """Emit the layer selection changed signal."""
        self.emit_signal(
            get_art_signal_code("LAYER_SELECTION_CHANGED"),
            {"selected_layer_ids": selected_layer_ids},
        )

    def update_grid_info(self, data: Dict) -> None:
        """Emit the canvas update grid info signal."""
        self.emit_signal(get_art_signal_code("CANVAS_UPDATE_GRID_INFO"), data)

    def interrupt_image_generation(self) -> None:
        """Emit the interrupt image generation signal."""
        self.emit_signal(get_art_signal_code("INTERRUPT_IMAGE_GENERATION_SIGNAL"))

    def send_image_to_canvas(self, image_response: ImageResponse) -> None:
        """Cache and emit one image response for the canvas."""
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
        """Emit the input image settings changed signal."""
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
        """Emit the canvas update image positions signal."""
        self.emit_signal(get_art_signal_code("CANVAS_UPDATE_IMAGE_POSITIONS"))

    def create_new_layer(self, **kwargs) -> Optional[CanvasLayer]:
        """Create a new canvas layer with default settings."""
        self.begin_layer_operation("create")
        layer = CanvasLayer.objects.create(**kwargs)
        if not layer:
            self.cancel_layer_operation("create")
            return None
        data = {"layer_id": layer.id}
        DrawingPadSettings.objects.create(**data)
        ImageToImageSettings.objects.create(**data)
        OutpaintSettings.objects.create(**data)
        self.commit_layer_operation("create", [layer.id])
        return layer

    def begin_layer_operation(
        self,
        action: str,
        layer_ids: Optional[list[int]] = None,
    ) -> None:
        """Emit the layer operation begin signal."""
        self.emit_signal(
            get_art_signal_code("LAYER_OPERATION_BEGIN"),
            {"action": action, "layer_ids": layer_ids or []},
        )

    def commit_layer_operation(
        self,
        action: str,
        layer_ids: Optional[list[int]] = None,
    ) -> None:
        """Emit the layer operation commit signal."""
        self.emit_signal(
            get_art_signal_code("LAYER_OPERATION_COMMIT"),
            {"action": action, "layer_ids": layer_ids or []},
        )

    def cancel_layer_operation(self, action: str) -> None:
        """Emit the layer operation cancel signal."""
        self.emit_signal(
            get_art_signal_code("LAYER_OPERATION_CANCEL"),
            {"action": action},
        )


__all__ = ["CanvasAPIService"]