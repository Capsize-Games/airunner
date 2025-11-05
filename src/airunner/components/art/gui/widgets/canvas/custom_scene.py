from dataclasses import asdict, is_dataclass
from typing import Optional, Dict, Any, List

from PIL import Image, ImageFilter
from PySide6.QtGui import QImage
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QGraphicsScene,
    QMessageBox,
)
from airunner.components.art.gui.widgets.canvas.simple_event import SimpleEvent

from airunner.components.art.data.canvas_layer import CanvasLayer

from airunner.enums import CanvasToolName, EngineResponseCode
from airunner.components.art.gui.widgets.canvas.mixins import (
    CanvasImageConversionMixin,
    CanvasSurfaceManagementMixin,
    CanvasMouseEventMixin,
    CanvasPainterMixin,
    CanvasItemManagementMixin,
    CanvasImageInitializationMixin,
    CanvasSceneManagementMixin,
    CanvasPositionUpdateMixin,
    CanvasLayerStructureMixin,
    CanvasInitializationMixin,
    CanvasActiveImageMixin,
    CanvasFilterMixin,
    CanvasTransformMixin,
    CanvasDragDropMixin,
    CanvasClipboardMixin,
    CanvasLayerMixin,
    CanvasHistoryMixin,
    CanvasPersistenceMixin,
    CanvasGenerationMixin,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.settings import (
    AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE,
)
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.art.managers.stablediffusion.rect import Rect
from airunner.components.art.utils.layer_compositor import LayerCompositor
from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.utils.image_filter_utils import (
    build_filter_object_from_model,
)


class CustomScene(
    CanvasImageConversionMixin,
    CanvasSurfaceManagementMixin,
    CanvasMouseEventMixin,
    CanvasPainterMixin,
    CanvasItemManagementMixin,
    CanvasImageInitializationMixin,
    CanvasSceneManagementMixin,
    CanvasPositionUpdateMixin,
    CanvasLayerStructureMixin,
    CanvasInitializationMixin,
    CanvasActiveImageMixin,
    CanvasFilterMixin,
    CanvasTransformMixin,
    CanvasDragDropMixin,
    CanvasClipboardMixin,
    CanvasLayerMixin,
    CanvasHistoryMixin,
    CanvasPersistenceMixin,
    CanvasGenerationMixin,
    MediatorMixin,
    SettingsMixin,
    QGraphicsScene,
):
    """Custom QGraphicsScene for AI Runner canvas with drawing, layer, and generation support.

    This class provides a modular canvas system with support for:
    - Drawing and erasing with brushes
    - Multi-layer composition and management
    - Image generation via Stable Diffusion
    - Filters and transformations
    - Undo/redo history
    - Drag-and-drop and clipboard operations

    The class uses mixins for separation of concerns and communicates via signals.
    """

    def __init__(self, canvas_type: str):
        super().__init__()
        self._initialize_canvas_state(canvas_type)
        self._register_canvas_signals()

    @property
    def original_item_positions(self) -> Dict[str, QPointF]:
        """Returns the original positions of items in the scene."""
        return self._original_item_positions

    @original_item_positions.setter
    def original_item_positions(self, value: Dict[str, QPointF]) -> None:
        """Set the original positions of items in the scene.

        Args:
            value: Dict mapping items to their original QPointF positions.
        """
        self._original_item_positions = value

    @property
    def current_tool(self) -> Optional[CanvasToolName]:
        """Get the currently active canvas tool.

        Returns:
            The active CanvasToolName, or None if no tool is active.
        """
        return (
            None
            if self.application_settings.current_tool is None
            else CanvasToolName(self.application_settings.current_tool)
        )

    @property
    def settings_key(self) -> str:
        """Get the current settings key from the property.

        Returns:
            The settings key string.
        """
        # Check for class attribute first (e.g., BrushScene.settings_key)
        if hasattr(self.__class__, "settings_key") and isinstance(
            getattr(self.__class__, "settings_key"), str
        ):
            return self.__class__.settings_key
        # Fall back to Qt property
        return self.property("settings_key")

    @property
    def current_settings(self) -> Any:
        """Get the current settings object based on settings_key.

        Returns:
            The active settings object (controlnet, image_to_image, outpaint, or drawing_pad).

        Raises:
            ValueError: If settings_key doesn't match any known settings type.
        """
        settings = None
        if self.settings_key == "controlnet_settings":
            settings = self.controlnet_settings
        elif self.settings_key == "image_to_image_settings":
            settings = self.image_to_image_settings
        elif self.settings_key == "outpaint_settings":
            settings = self.outpaint_settings
        elif self.settings_key == "drawing_pad_settings":
            settings = self.drawing_pad_settings
        if not settings:
            raise ValueError(
                f"Settings is not set. Settings not found for key: {self.settings_key}"
            )
        return settings

    @property
    def image_pivot_point(self) -> QPointF:
        """Get the current image pivot point from settings.

        Returns:
            QPointF representing the pivot point coordinates, or (0, 0) if not available.
        """
        if hasattr(self.current_settings, "x_pos") and hasattr(
            self.current_settings, "y_pos"
        ):
            return QPointF(
                self.current_settings.x_pos, self.current_settings.y_pos
            )
        return QPointF(0, 0)

    @property
    def is_brush_or_eraser(self) -> bool:
        """Check if current tool is brush or eraser.

        Returns:
            True if current tool is BRUSH or ERASER, False otherwise.
        """
        return self.current_tool in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER,
        )

    @property
    def layer_compositor(self) -> LayerCompositor:
        """Get the LayerCompositor instance for this scene.

        Returns:
            The LayerCompositor instance used for compositing layers.
        """
        if not hasattr(self, "_layer_compositor"):
            self._layer_compositor = LayerCompositor()
        return self._layer_compositor

    @image_pivot_point.setter
    def image_pivot_point(self, value: QPointF) -> None:
        """Set the image pivot point and update current layer.

        Args:
            value: The new pivot point coordinates.
        """
        self.api.art.canvas.update_current_layer(value)

    def handle_cursor(self, event: Any, apply_cursor: bool = True) -> None:
        """Handle cursor updates for the canvas.

        Args:
            event: The Qt event triggering cursor update.
            apply_cursor: Whether to actually apply the cursor change.
        """
        self._handle_cursor(event, apply_cursor)

    def _apply_auto_filters(self) -> None:
        """Apply all auto-apply filters from database to the current image."""
        try:
            auto_filters = ImageFilter.objects.filter_by(auto_apply=True) or []
            for f in auto_filters:
                try:
                    filter_obj = build_filter_object_from_model(f)
                    if filter_obj is not None:
                        self.api.art.image_filter.apply(filter_obj)
                except Exception:
                    self.logger.exception(
                        "Failed to auto-apply filter %s",
                        getattr(f, "name", "<unknown>"),
                    )
        except Exception:
            self.logger.exception("Error while applying auto filters")

    def on_image_generated_signal(self, data: Dict[str, Any]) -> None:
        """Handle image generation completion signal.

        Args:
            data: Dictionary containing generation result, code, message, and optional callback.
        """
        code = data["code"]
        callback = data.get("callback", None)

        if code in (
            EngineResponseCode.INSUFFICIENT_GPU_MEMORY,
            EngineResponseCode.ERROR,
        ):
            if self.settings_key == "drawing_pad_settings":
                message = data.get("message")
                self.api.application_error(message)
                self.display_gpu_memory_error(message)
        elif code is EngineResponseCode.INTERRUPTED:
            pass
        elif code is EngineResponseCode.IMAGE_GENERATED:
            self._handle_image_generated_signal(data)
            self._apply_auto_filters()

        if self.settings_key == "drawing_pad_settings":
            if callback:
                callback(data)
            self.api.art.stop_progress_bar()

    def display_gpu_memory_error(self, message: str) -> None:
        """Display a GPU memory error dialog with optional CPU offload option.

        Args:
            message: The error message to display.
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error: Unable to Generate Image")
        msg_box.setText(message)

        enable_cpu_offload_button = None
        if message == AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE:
            enable_cpu_offload_button = msg_box.addButton(
                "Enable CPU offload", QMessageBox.ButtonRole.AcceptRole
            )

        msg_box.exec()

        if (
            enable_cpu_offload_button
            and msg_box.clickedButton() == enable_cpu_offload_button
        ):
            self.enable_cpu_offload_callback()

    def enable_cpu_offload_callback(self) -> None:
        """Enable CPU offload in memory settings to handle GPU memory constraints."""
        self.update_memory_settings(enable_model_cpu_offload=True)

    def on_canvas_clear_signal(self) -> None:
        """Handle canvas clear signal by resetting image and history."""
        self.current_active_image = None
        self.delete_image()
        self._clear_history()
        self.api.art.canvas.recenter_grid()

    def on_mask_layer_toggled(self) -> None:
        """Handle mask layer toggle by reinitializing the image."""
        self.initialize_image()

    def on_settings_changed(self, data: Dict[str, Any]) -> None:
        """Handle settings changed signal.

        Args:
            data: Dictionary with setting_name, column_name, and value.
        """
        data["setting_name"]
        data["column_name"]
        data["value"]

    def _serialize_record(self, obj: Any) -> Optional[Dict[str, Any]]:
        if obj is None:
            return None
        if is_dataclass(obj):
            return asdict(obj)
        if hasattr(obj, "to_dict"):
            try:
                return obj.to_dict()
            except Exception:
                pass
        if isinstance(obj, dict):
            return dict(obj)
        try:
            return dict(vars(obj))
        except Exception:
            return None

    def _capture_layer_orders(self) -> List[Dict[str, int]]:
        layers = CanvasLayer.objects.all()
        if not layers:
            return []
        sorted_layers = sorted(
            layers, key=lambda layer: getattr(layer, "order", 0)
        )
        orders: List[Dict[str, int]] = []
        for index, layer in enumerate(sorted_layers):
            layer_id = getattr(layer, "id", None)
            if layer_id is None:
                continue
            order_value = getattr(layer, "order", index)
            orders.append({"layer_id": layer_id, "order": order_value})
        return orders

    def show_event(self) -> None:
        """Handle show event for the scene."""
        self.handle_cached_send_image_to_canvas()

    def _release_painter_for_device(self, device: Optional[QImage]):
        if device is not None and device is self._painter_target:
            self.stop_painter()

    def _update_current_settings(self, key, value):
        if self.settings_key == "controlnet_settings":
            self.update_controlnet_settings(**{key: value})
        elif self.settings_key == "image_to_image_settings":
            self.update_image_to_image_settings(**{key: value})
        elif self.settings_key == "outpaint_settings":
            self.update_outpaint_settings(**{key: value})
        elif self.settings_key == "drawing_pad_settings":
            self.update_drawing_pad_settings(**{key: value})

    def _create_image(
        self,
        image: Image.Image,
        is_outpaint: bool,
        outpaint_box_rect: Optional[Rect] = None,
        generated: bool = False,
    ):
        if not generated and self.application_settings.resize_on_paste:
            image = self._resize_image(image)

        self._add_image_to_scene(
            image,
            is_outpaint=is_outpaint,
            outpaint_box_rect=outpaint_box_rect,
            generated=generated,
        )

        self.api.art.canvas.image_updated()

    def _set_current_active_image(self, image: Image):
        self.initialize_image(image)

    def _handle_cursor(self, event, apply_cursor: bool = True):
        if hasattr(self, "_last_cursor_state"):
            current_state = (event.type(), apply_cursor)
            if self._last_cursor_state == current_state:
                return
        self._last_cursor_state = (event.type(), apply_cursor)
        evt = event if hasattr(event, "button") else SimpleEvent(event)
        if self.api and hasattr(self.api, "art") and self.api.art:
            self.api.art.canvas.update_cursor(evt, apply_cursor)

    @staticmethod
    def _load_image(image_path: str) -> Image:
        image = Image.open(image_path)
        return image

    def get_canvas_offset(self) -> QPointF:
        """Get the current canvas offset from the view.

        Returns:
            The canvas offset as a QPointF, or (0, 0) if no view available.
        """
        if self.views() and hasattr(self.views()[0], "canvas_offset"):
            return self.views()[0].canvas_offset
        return QPointF(0, 0)
