import io
import logging
import os
import subprocess
import time
from typing import Optional, Tuple, Dict

import PIL
from PIL import ImageQt, Image, ImageFilter
from PySide6.QtGui import QImage
from PySide6.QtCore import Qt, QPoint, QRect, QPointF
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QDragMoveEvent,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QGraphicsScene,
    QFileDialog,
    QGraphicsSceneMouseEvent,
    QMessageBox,
)
from line_profiler import profile

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings

logger = logging.getLogger(__name__)
import requests  # Added for HTTP(S) image download

from airunner.enums import SignalCode, CanvasToolName, EngineResponseCode
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.settings import (
    AIRUNNER_VALID_IMAGE_FILES,
    AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE,
)
from airunner.utils.image import (
    export_image,
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.components.art.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.art.managers.stablediffusion.rect import Rect
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.components.art.utils.layer_compositor import LayerCompositor
from airunner.utils.settings.get_qsettings import get_qsettings


class CustomScene(
    MediatorMixin,
    SettingsMixin,
    QGraphicsScene,
):
    def __init__(self, canvas_type: str):
        self._is_erasing = None
        self._is_drawing = None
        self.canvas_type = canvas_type
        self.image_backup = None
        # Cache for current_active_image to avoid redundant binary conversions
        self._current_active_image_ref = None
        self._current_active_image_binary = None
        self.previewing_filter = False
        self.painter = None
        self.image: Optional[QImage] = None
        self.item: Optional[DraggablePixmap] = None
        self._image_initialized: bool = False
        super().__init__()
        self.last_export_path = None
        self._target_size = None
        self.settings = get_qsettings()

        # Add a variable to store the last mouse position
        self.last_pos = None
        self.start_pos = None
        self.selection_start_pos = None
        self.selection_stop_pos = None
        self.do_update = False
        self.generate_image_time_in_ms = 0.5
        self.do_generate_image = False
        self.generate_image_time = 0
        self.undo_history = []
        self.redo_history = []
        self.right_mouse_button_pressed = False
        self.handling_event = False
        self._original_item_positions = {}  # Store original positions of items
        # Debounce timer for persisting current_active_image to DB
        self._persist_timer = QTimer()
        self._persist_timer.setSingleShot(True)
        self._persist_timer.timeout.connect(self._flush_pending_image)
        self._pending_image_binary = None
        self._pending_image_generation = (
            0  # monotonic counter to ensure latest wins
        )
        # Performance feature flags / caches
        self._raw_image_storage_enabled = (
            True  # Re-enable raw RGBA storage for speed
        )
        self._current_active_image_hash = None  # lightweight change detector
        self._qimage_cache = None  # last QImage
        self._qimage_cache_size = None
        self._qimage_cache_hash = None  # hash of cached QImage content
        # Cache for expensive database settings queries
        self._active_grid_cache = None
        self._active_grid_cache_time = 0

        # Add viewport rectangle that includes negative space
        self._extended_viewport_rect = QRect(-2000, -2000, 4000, 4000)

        # Layer rendering system
        self._layer_items = (
            {}
        )  # Maps layer_id to LayerImageItem graphics items
        self._layers_initialized = False

        for signal, handler in [
            (
                SignalCode.CANVAS_COPY_IMAGE_SIGNAL,
                self.on_canvas_copy_image_signal,
            ),
            (
                SignalCode.CANVAS_CUT_IMAGE_SIGNAL,
                self.on_canvas_cut_image_signal,
            ),
            (
                SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL,
                self.on_canvas_rotate_90_clockwise_signal,
            ),
            (
                SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL,
                self.on_canvas_rotate_90_counterclockwise_signal,
            ),
            (
                SignalCode.CANVAS_PASTE_IMAGE_SIGNAL,
                self.on_paste_image_from_clipboard,
            ),
            (
                SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL,
                self.on_export_image_signal,
            ),
            (
                SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL,
                self.on_import_image_signal,
            ),
            (
                SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
                self.on_send_image_to_canvas_signal,
            ),
            (
                SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
                self.on_apply_filter_signal,
            ),
            (
                SignalCode.CANVAS_CANCEL_FILTER_SIGNAL,
                self.on_cancel_filter_signal,
            ),
            (
                SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
                self.on_preview_filter_signal,
            ),
            (
                SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL,
                self.on_load_image_from_path,
            ),
            (
                SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
                self.on_image_generated_signal,
            ),
            (SignalCode.UNDO_SIGNAL, self.on_action_undo_signal),
            (SignalCode.REDO_SIGNAL, self.on_action_redo_signal),
            (SignalCode.HISTORY_CLEAR_SIGNAL, self.on_clear_history_signal),
            (SignalCode.CANVAS_CLEAR, self.on_canvas_clear_signal),
            (SignalCode.MASK_LAYER_TOGGLED, self.on_mask_layer_toggled),
            (
                SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
                self.on_settings_changed,
            ),
            (
                SignalCode.LAYER_VISIBILITY_TOGGLED,
                self.on_layer_visibility_toggled,
            ),
            (
                SignalCode.LAYER_DELETED,
                self.on_layer_deleted,
            ),
            (
                SignalCode.LAYER_REORDERED,
                self.on_layer_reordered,
            ),
            (
                SignalCode.LAYERS_SHOW_SIGNAL,
                self.on_layers_show_signal,
            ),
        ]:
            self.register(signal, handler)

    @property
    def original_item_positions(self) -> Dict[str, QPointF]:
        """Returns the original positions of items in the scene."""
        return self._original_item_positions

    @property
    def current_tool(self):
        return (
            None
            if self.application_settings.current_tool is None
            else CanvasToolName(self.application_settings.current_tool)
        )

    @property
    def settings_key(self):
        return self.property("settings_key")

    @property
    def current_settings(self):
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
    def image_pivot_point(self):
        if hasattr(self.current_settings, "x_pos") and hasattr(
            self.current_settings, "y_pos"
        ):
            return QPointF(
                self.current_settings.x_pos, self.current_settings.y_pos
            )
        return QPointF(0, 0)

    @property
    def current_active_image(self) -> Image:
        # Fast path: return cached reference if available
        if self._current_active_image_ref is not None:
            return self._current_active_image_ref
        binary_data = self.current_settings.image
        if binary_data is None:
            return None
        # Attempt raw fast decode inline to avoid extra function overhead
        if (
            isinstance(binary_data, (bytes, bytearray))
            and binary_data.startswith(b"AIRAW1")
            and len(binary_data) >= 14
        ):
            try:
                w = int.from_bytes(binary_data[6:10], "big")
                h = int.from_bytes(binary_data[10:14], "big")
                rgba = binary_data[14:]
                if len(rgba) == w * h * 4:
                    img = Image.frombuffer(
                        "RGBA", (w, h), rgba, "raw", "RGBA", 0, 1
                    ).copy()
                    self._current_active_image_ref = img
                    self._current_active_image_binary = binary_data
                    return img
            except Exception as e:
                self.logger.error(f"Error decoding AIRAW1 image: {e}")
        # Fallback to general converter
        try:
            img = convert_binary_to_image(binary_data)
            self._current_active_image_ref = img
            self._current_active_image_binary = (
                binary_data if img is not None else None
            )
            return img
        except OSError as e:
            # Catch libpng errors specifically
            self.logger.error(f"Image format error (libpng/PIL): {e}")
            return None
        except Exception as e:
            self.logger.error(f"General error loading image: {e}")
            return None

    @current_active_image.setter
    def current_active_image(self, image: Image):
        """Set the current active image, avoiding unnecessary DB writes.

        The original implementation always converted and persisted the image.
        This adds a small optimization: skip the DB update if the incoming
        image (after conversion) matches what is already stored. This helps
        when UI paths redundantly reassign the same image object.
        """
        if image is not None and not isinstance(image, Image.Image):
            return

        if image is None:
            settings = self.current_settings  # cache to avoid double load
            if (
                settings.image is not None
                or self._pending_image_binary is not None
            ):
                # Clear pending and persisted
                self._pending_image_binary = None
                self._current_active_image_binary = None
                self._current_active_image_ref = None
                # Immediate flush
                self._update_current_settings("image", None)
                if self.settings_key == "drawing_pad_settings":
                    self.api.art.canvas.image_updated()
            return

        # Convert to binary for comparison & persistence
        settings = self.current_settings  # cache

        # Fast identity check: same object reference -> skip
        if image is self._current_active_image_ref:
            return

        # Quick size/mode change check before expensive conversion
        if self._current_active_image_ref is not None:
            if (
                image.size == self._current_active_image_ref.size
                and image.mode == self._current_active_image_ref.mode
            ):
                # Same size/mode - check if it's actually the same data
                try:
                    if (
                        image.tobytes()
                        == self._current_active_image_ref.tobytes()
                    ):
                        return  # Identical image data, skip update
                except:
                    pass  # Fall through to normal processing if tobytes fails

        # Raw storage path (faster than PNG) else fallback
        if self._raw_image_storage_enabled:
            try:
                rgba = image if image.mode == "RGBA" else image.convert("RGBA")
                w, h = rgba.size
                header = (
                    b"AIRAW1" + w.to_bytes(4, "big") + h.to_bytes(4, "big")
                )
                binary_image = header + rgba.tobytes()
            except Exception:
                # Raw encoding failed, fallback to PNG
                binary_image = convert_image_to_binary(image)
        else:
            binary_image = convert_image_to_binary(image)

        if self._current_active_image_binary == binary_image:
            self._current_active_image_ref = image
            return

        self._current_active_image_ref = image
        self._current_active_image_binary = binary_image

        # Debounced persistence: schedule DB update rather than immediate commit.
        self._pending_image_binary = binary_image
        self._pending_image_generation += 1
        generation = self._pending_image_generation
        # Restart timer (150ms window)
        self._persist_timer.start(150)
        # Optionally notify lightweight listeners about in-memory change only
        if self.settings_key == "drawing_pad_settings":
            # Do not spam full image_updated if nothing rendered changes; here we allow it
            self.api.art.canvas.image_updated()

    def _flush_pending_image(self):
        """Persist the most recent pending image binary to settings (debounced)."""
        if self._pending_image_binary is None:
            return
        # If already persisted, skip
        if self.current_settings.image == self._pending_image_binary:
            self._pending_image_binary = None
            return
        self._update_current_settings("image", self._pending_image_binary)
        self._pending_image_binary = None

    def _binary_to_pil_fast(self, binary_data: bytes) -> Optional[Image.Image]:
        """Fast inverse for raw storage format; fallback to existing converter.

        Raw format layout: b"AIRAW1" + 4 bytes width + 4 bytes height + RGBA bytes.
        """
        if binary_data is None:
            return None
        try:
            if binary_data.startswith(b"AIRAW1") and len(binary_data) > 14:
                w = int.from_bytes(binary_data[6:10], "big")
                h = int.from_bytes(binary_data[10:14], "big")
                rgba = binary_data[14:]
                if len(rgba) == w * h * 4:
                    return Image.frombuffer(
                        "RGBA", (w, h), rgba, "raw", "RGBA", 0, 1
                    )
        except Exception:
            pass
        return convert_binary_to_image(binary_data)

    @property
    def is_brush_or_eraser(self):
        return self.current_tool in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER,
        )

    @property
    def layer_compositor(self):
        """Get the LayerCompositor instance for this scene."""
        if not hasattr(self, "_layer_compositor"):
            self._layer_compositor = LayerCompositor()
        return self._layer_compositor

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        self.api.art.canvas.update_current_layer(value)

    def handle_cursor(self, event, apply_cursor: bool = True):
        self._handle_cursor(event, apply_cursor)

    def on_clear_history_signal(self):
        self._clear_history()

    def on_export_image_signal(self):
        image = self.current_active_image
        if image:
            parent_window = self.views()[0].window()
            initial_dir = (
                self.last_export_path if self.last_export_path else ""
            )
            file_dialog = QFileDialog(
                parent_window,
                "Save Image",
                initial_dir,
                f"Image Files ({' '.join(AIRUNNER_VALID_IMAGE_FILES)})",
            )
            file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
                file_path = file_dialog.selectedFiles()[0]
                if file_path == "":
                    return
                self.last_export_path = os.path.dirname(file_path)
                if not file_path.endswith(AIRUNNER_VALID_IMAGE_FILES):
                    file_path = f"{file_path}.png"
                export_image(image, file_path)

    def on_import_image_signal(self):
        if self.settings_key != "drawing_pad_settings":
            return
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            "",
            f"Image Files ({' '.join(AIRUNNER_VALID_IMAGE_FILES)})",
        )
        if file_path == "":
            return
        self.on_load_image_signal(file_path)

    def on_send_image_to_canvas_signal(self, data: Dict):
        """Handle generated image by creating a new layer."""
        image_response: ImageResponse = data.get("image_response")
        if not image_response or not image_response.images:
            return

        image = image_response.images[0]

        # Create a new layer from the generated image
        layer_id = self.layer_compositor.create_layer_from_image(
            image=image, name="Generated Image"
        )

        # Emit signal to refresh the layer container to show the new layer
        self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)

        # Refresh the canvas display to show the new layer
        self._refresh_layer_display()

    def on_paste_image_from_clipboard(self):
        image = self._paste_image_from_clipboard()
        if image is None:
            return
        if not isinstance(image, Image.Image):
            return
        if self.application_settings.resize_on_paste:
            image = self._resize_image(image)
        self.current_active_image = image
        self.refresh_image(image)

    def on_load_image_from_path(self, message):
        image_path = message["image_path"]
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self._load_image_from_object(image)

    def on_load_image_signal(self, image_path: str):
        self._add_image_to_undo()
        image = self._load_image(image_path)
        if self.application_settings.resize_on_paste:
            image = self._resize_image(image)
        self.current_active_image = image
        self.initialize_image(image)

    def on_apply_filter_signal(self, message):
        self._apply_filter(message)

    def on_cancel_filter_signal(self):
        image = self._cancel_filter()
        if image:
            self._load_image_from_object(image=image)

    def on_preview_filter_signal(self, message):
        filter_object: ImageFilter.Filter = message["filter_object"]
        filtered_image = self._preview_filter(
            self.current_active_image, filter_object
        )
        self._load_image_from_object(image=filtered_image)

    def on_image_generated_signal(self, data: Dict):
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
        else:
            if self.settings_key == "drawing_pad_settings":
                pass

        if self.settings_key == "drawing_pad_settings":
            self.api.art.stop_progress_bar()
            if callback:
                callback(data)

    @profile
    def _handle_image_generated_signal(self, data: Dict):
        image_response: Optional[ImageResponse] = data.get("message", None)
        if image_response is None:
            return
        images = image_response.images
        if len(images) == 0:
            pass
        elif image_response and not getattr(image_response, "node_id", None):
            outpaint_box_rect = image_response.active_rect
            # Optimize: Only convert if absolutely necessary and cache conversion
            image = images[0]
            # Use lazy conversion - defer RGBA conversion until QImage creation
            self._create_image(
                image=image,
                is_outpaint=image_response.is_outpaint,
                outpaint_box_rect=outpaint_box_rect,
                generated=True,
            )
            # Force immediate persistence to avoid race condition with undo operations
            self._flush_pending_image()
            # Refresh layer display to show the newly generated image
            self._refresh_layer_display()
            # Defer batch image update to not block UI
            QTimer.singleShot(
                100, lambda: self.api.art.update_batch_images(images)
            )

    def display_gpu_memory_error(self, message: str):
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

    def enable_cpu_offload_callback(self):
        self.update_memory_settings(enable_model_cpu_offload=True)

    def on_canvas_clear_signal(self):
        self.current_active_image = None
        self.delete_image()
        self._clear_history()
        self.api.art.canvas.recenter_grid()

    def on_mask_layer_toggled(self):
        self.initialize_image()

    def on_settings_changed(self, data):
        table = data["setting_name"]
        column_name = data["column_name"]
        value = data["value"]

    def on_canvas_copy_image_signal(self):
        self._copy_image(self.current_active_image)

    def on_canvas_cut_image_signal(self):
        self._cut_image(self.current_active_image)

    def on_canvas_rotate_90_clockwise_signal(self):
        self._rotate_90_clockwise()

    def on_canvas_rotate_90_counterclockwise_signal(self):
        self._rotate_90_counterclockwise()

    def on_action_undo_signal(self):
        if len(self.undo_history) == 0:
            return
        data = self.undo_history.pop()
        self._add_image_to_redo()
        self._history_set_image(data)
        view = self.views()[0]
        view.updateImagePositions()

    def on_action_redo_signal(self):
        if len(self.redo_history) == 0:
            return
        data = self.redo_history.pop()
        self._add_image_to_undo()
        self._history_set_image(data)
        view = self.views()[0]
        view.updateImagePositions()

    def _history_set_image(self, data: Dict):
        if data is not None:
            if data["image"] is None:
                self.delete_image()
            else:
                self.current_active_image = data["image"]
                self.initialize_image(self.current_active_image)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._image_initialized:
            self._image_initialized = True
            self.initialize_image()
        if not self._layers_initialized:
            self._layers_initialized = True
            self._refresh_layer_display()

    # Layer management signal handlers
    def on_layer_visibility_toggled(self, data: Dict):
        """Handle layer visibility changes."""
        layer_id = data.get("layer_id")
        visible = data.get("visible")

        self.logger.info(
            f"Layer visibility toggled: layer_id={layer_id}, visible={visible}"
        )

        if layer_id in self._layer_items:
            layer_item = self._layer_items[layer_id]
            layer_item.setVisible(visible)
            self.logger.info(f"Updated layer item visibility: {visible}")
        else:
            self.logger.warning(
                f"Layer item not found for layer_id={layer_id}"
            )
            # Try to refresh the entire display
            self._refresh_layer_display()

    def on_layer_deleted(self, data: Dict):
        """Handle layer deletion by removing its graphics item."""
        layer_id = data.get("layer_id")

        if layer_id in self._layer_items:
            layer_item = self._layer_items[layer_id]
            if layer_item.scene():
                layer_item.scene().removeItem(layer_item)
            del self._layer_items[layer_id]

    def on_layer_reordered(self, data: Dict):
        """Handle layer reordering by updating z-values."""
        self._refresh_layer_display()

    def on_layers_show_signal(self, data: Dict = None):
        """Handle layer container refresh signal."""
        self._refresh_layer_display()

    def _refresh_layer_display(self):
        """Refresh the display of all visible layers on the canvas."""
        logger.info("Refreshing layer display")
        logger.debug(
            f"Current scene items before refresh: {len(self.items())}"
        )
        logger.debug(
            f"Current _layer_items before refresh: {list(self._layer_items.keys())}"
        )

        try:
            from airunner.components.art.data.drawingpad_settings import (
                DrawingPadSettings,
            )
            from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
                LayerImageItem,
            )
            from airunner.utils.image import convert_binary_to_image
            from PySide6.QtGui import QImage
            from PIL.ImageQt import ImageQt

            # Get all layers ordered by their order property
            layers = CanvasLayer.objects.order_by("order").all()
            logger.info(f"Found {len(layers)} layers to display")

            # If we have layers, remove the old drawing pad item to prevent duplication
            if (
                len(layers) > 0
                and hasattr(self, "item")
                and self.item is not None
            ):
                logger.debug(
                    "Removing old drawing pad item to use layer system"
                )
                if self.item.scene():
                    self.removeItem(self.item)
                self.item = None

            # Remove any layer items that no longer exist
            existing_layer_ids = {layer.id for layer in layers}
            items_to_remove = []
            for layer_id, item in self._layer_items.items():
                if layer_id not in existing_layer_ids:
                    items_to_remove.append(layer_id)

            for layer_id in items_to_remove:
                logger.info(f"Removing deleted layer {layer_id} from scene")
                item = self._layer_items[layer_id]
                if item.scene():
                    item.scene().removeItem(item)
                del self._layer_items[layer_id]

            # Create or update layer items for each layer
            for layer in layers:
                logger.debug(
                    f"Processing layer {layer.id}: name={layer.name}, visible={layer.visible}"
                )

                # Get the corresponding DrawingPadSettings for this layer
                drawing_pad_settings = None
                try:
                    results = DrawingPadSettings.objects.filter_by(
                        layer_id=layer.id
                    )
                    drawing_pad_settings = results[0] if results else None
                    logger.debug(
                        f"Found DrawingPadSettings for layer {layer.id}: {drawing_pad_settings is not None}"
                    )
                except Exception as e:
                    logger.debug(
                        f"No DrawingPadSettings found for layer {layer.id}: {e}"
                    )

                if drawing_pad_settings and drawing_pad_settings.image:
                    # Convert binary image data to PIL Image
                    pil_image = convert_binary_to_image(
                        drawing_pad_settings.image
                    )
                    logger.debug(
                        f"Layer {layer.id} has image from DrawingPadSettings"
                    )

                    if pil_image:
                        # Convert PIL Image to QImage
                        qimage = ImageQt(pil_image)

                        if layer.id in self._layer_items:
                            # Update existing layer item
                            layer_item = self._layer_items[layer.id]
                            logger.debug(
                                f"Updating existing layer item {layer.id} - setting visible={layer.visible}"
                            )
                            if hasattr(layer_item, "updateImage"):
                                layer_item.updateImage(qimage)
                            layer_item.setVisible(layer.visible)
                            layer_item.setOpacity(layer.opacity / 100.0)
                            # Invert Z-order: lower order numbers should be on top
                            # Use a high base value and subtract the order
                            layer_item.setZValue(1000 - layer.order)

                            # Update position if drawing_pad_settings has changed
                            if drawing_pad_settings:
                                if (
                                    drawing_pad_settings.x_pos is not None
                                    and drawing_pad_settings.y_pos is not None
                                ):
                                    new_pos = QPointF(
                                        drawing_pad_settings.x_pos,
                                        drawing_pad_settings.y_pos,
                                    )
                                    if (
                                        layer_item
                                        not in self.original_item_positions
                                        or self.original_item_positions[
                                            layer_item
                                        ]
                                        != new_pos
                                    ):
                                        self.original_item_positions[
                                            layer_item
                                        ] = new_pos
                                        # Apply canvas offset to get current visible position
                                        canvas_offset = (
                                            self.get_canvas_offset()
                                        )
                                        visible_pos = new_pos - canvas_offset
                                        layer_item.setPos(visible_pos)
                        else:
                            # Create new layer item
                            logger.debug(
                                f"Creating new layer item {layer.id} - setting visible={layer.visible}"
                            )
                            layer_item = LayerImageItem(qimage)
                            layer_item.setVisible(layer.visible)
                            layer_item.setOpacity(layer.opacity / 100.0)
                            # Invert Z-order: lower order numbers should be on top
                            layer_item.setZValue(1000 - layer.order)

                            # Add to scene
                            self.addItem(layer_item)
                            self._layer_items[layer.id] = layer_item

                            # Set position: prefer active grid settings for newly generated content,
                            # fallback to drawing_pad_settings for existing content
                            if (
                                drawing_pad_settings
                                and drawing_pad_settings.x_pos is not None
                                and drawing_pad_settings.y_pos is not None
                            ):
                                # Use stored position from drawing_pad_settings
                                x_pos = drawing_pad_settings.x_pos
                                y_pos = drawing_pad_settings.y_pos
                            else:
                                # Use active grid settings position (for newly generated content)
                                x_pos = (
                                    self.active_grid_settings.pos_x
                                    if hasattr(self, "active_grid_settings")
                                    else 0
                                )
                                y_pos = (
                                    self.active_grid_settings.pos_y
                                    if hasattr(self, "active_grid_settings")
                                    else 0
                                )

                                # Update drawing_pad_settings with the active grid position
                                if drawing_pad_settings:
                                    try:
                                        self.update_drawing_pad_settings(
                                            x_pos=x_pos, y_pos=y_pos
                                        )
                                    except Exception as e:
                                        logger.debug(
                                            f"Failed to update drawing pad settings position: {e}"
                                        )

                            # Apply canvas offset to position the item correctly in the current view
                            canvas_offset = self.get_canvas_offset()
                            visible_pos = QPointF(x_pos, y_pos) - canvas_offset
                            layer_item.setPos(visible_pos)

                            # Track original position for canvas recentering
                            self.original_item_positions[layer_item] = QPointF(
                                x_pos, y_pos
                            )
                else:
                    # Layer has no drawing pad settings with image, remove its item if it exists
                    if layer.id in self._layer_items:
                        logger.debug(
                            f"Layer {layer.id} has no image in DrawingPadSettings, removing from scene"
                        )
                        item = self._layer_items[layer.id]
                        if item.scene():
                            item.scene().removeItem(item)
                        del self._layer_items[layer.id]

            logger.debug(
                f"Current scene items after refresh: {len(self.items())}"
            )
            logger.debug(
                f"Current _layer_items after refresh: {list(self._layer_items.keys())}"
            )

        except Exception as e:
            self.logger.error(f"Error refreshing layer display: {e}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # Accept if any URL is a valid image (local file or http(s))
            for url in event.mimeData().urls():
                url_str = url.toString()
                if url_str.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".bmp", ".gif")
                ) or url_str.startswith("http"):
                    event.acceptProposedAction()
                    return
            event.ignore()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        if hasattr(self, "logger"):
            self.logger.debug(f"Drop mime types: {mime.formats()}")
        handled = False
        # Try raw image data (e.g. 'image/png')
        for fmt in mime.formats():
            if fmt.startswith("image/"):
                data = mime.data(fmt)
                try:
                    # Validate data before opening
                    if data.size() < 10:  # Minimum size check
                        continue
                    data_bytes = data.data()
                    if not data_bytes or len(data_bytes) < 10:
                        continue
                    img = Image.open(io.BytesIO(data_bytes))
                    # Verify the image can be loaded
                    img.verify()
                    # Reopen since verify() consumes the image
                    img = Image.open(io.BytesIO(data_bytes))
                    self._add_image_to_undo()
                    if self.application_settings.resize_on_paste:
                        img = self._resize_image(img)
                    self.current_active_image = img
                    self.initialize_image(img)
                    handled = True
                    break
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.debug(
                            f"Failed to load image from {fmt}: {e}"
                        )
                    continue
        if not handled and mime.hasUrls():
            for url in mime.urls():
                url_str = url.toString()
                img = self._load_image_from_url_or_file(url_str)
                if img is not None:
                    self._add_image_to_undo()
                    if self.application_settings.resize_on_paste:
                        img = self._resize_image(img)
                    self.current_active_image = img
                    self.initialize_image(img)
                    handled = True
                    break
                # fallback: try as file path
                path = url.toLocalFile()
                if path:
                    img = self._load_image_from_url_or_file(path)
                    if img is not None:
                        self._add_image_to_undo()
                        if self.application_settings.resize_on_paste:
                            img = self._resize_image(img)
                        self.current_active_image = img
                        self.initialize_image(img)
                        handled = True
                        break
        if handled:
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def wheelEvent(self, event):
        if not hasattr(event, "delta"):
            return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = self.grid_settings.zoom_in_step
            zoom_out_factor = -self.grid_settings.zoom_out_step

            if event.delta() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor

            zoom_level = self.grid_settings.zoom_level
            zoom_level += zoom_factor
            if zoom_level < 0.1:
                zoom_level = 0.1
            self.update_grid_settings(zoom_level=zoom_level)
            self.api.art.canvas.zoom_level_changed()

    def mousePressEvent(self, event):
        if isinstance(event, QGraphicsSceneMouseEvent):
            if event.button() == Qt.MouseButton.RightButton:
                self.right_mouse_button_pressed = True
                self.start_pos = event.scenePos()
            elif event.button() == Qt.MouseButton.LeftButton:
                super(CustomScene, self).mousePressEvent(event)
        self._handle_cursor(event)
        self.last_pos = event.scenePos()
        self.update()

        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_left_mouse_press(event)
            self._handle_cursor(event)
            if not self.is_brush_or_eraser:
                super().mousePressEvent(event)
            elif self.drawing_pad_settings.enable_automatic_drawing:
                self.api.art.canvas.interrupt_image_generation()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_mouse_button_pressed = False
        else:
            self._handle_left_mouse_release(event)
            super(CustomScene, self).mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)
        self._handle_cursor(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_pos = None
            self.start_pos = None
            self.do_update = False
            if self.drawing_pad_settings.enable_automatic_drawing:
                if self._is_drawing or self._is_erasing:
                    self.api.art.generate_image()
            self._is_drawing = False
            self._is_erasing = False

    def mouseMoveEvent(self, event):
        if self.right_mouse_button_pressed:
            view = self.views()[0]
            view.setTransformationAnchor(view.ViewportAnchor.NoAnchor)
            view.setResizeAnchor(view.ViewportAnchor.NoAnchor)
            delta = event.scenePos() - self.last_pos
            scale_factor = view.transform().m11()
            view.translate(delta.x() / scale_factor, delta.y() / scale_factor)
            self.last_pos = event.scenePos()
        else:
            super(CustomScene, self).mouseMoveEvent(event)

        self.last_pos = event.scenePos()
        self.update()

    def enterEvent(self, event):
        self._handle_cursor(event, True)

    def leaveEvent(self, event):
        self._handle_cursor(event, False)

    def refresh_image(self, image: Image = None):
        view = self.views()[0]
        current_viewport_rect = view.mapToScene(
            view.viewport().rect()
        ).boundingRect()

        if self.painter and self.painter.isActive():
            self.painter.end()

        try:
            item_scene = self.item.scene()
        except AttributeError:
            item_scene = None
        if item_scene is not None:
            item_scene.removeItem(self.item)
        self.initialize_image(image)
        view.setSceneRect(current_viewport_rect)

    def delete_image(self):
        # Safely remove the image item from the scene (if present)
        try:
            item_scene = self.item.scene()
        except AttributeError:
            item_scene = None
        if item_scene is not None:
            item_scene.removeItem(self.item)

        # Properly end and reset the painter so drawBackground can reinitialize
        if self.painter and self.painter.isActive():
            self.painter.end()
        self.painter = None
        self.current_active_image = None
        self.image = None
        if hasattr(self, "item") and self.item is not None:
            del self.item
        self.item = None

    def set_image(self, pil_image: Image = None):
        base64image = None
        if not pil_image:
            # Use cached reference first to avoid database lookup during pending persistence
            pil_image = self._current_active_image_ref
            if pil_image is None:
                # Fallback to loading from database if no cached reference
                base64image = self.current_settings.image

        if base64image is not None:
            try:
                pil_image = convert_binary_to_image(base64image)
                if pil_image is not None:
                    pil_image = pil_image.convert("RGBA")
            except AttributeError as e:
                pil_image = None
            except PIL.UnidentifiedImageError as e:
                pil_image = None
            except Exception as e:
                pil_image = None

        if pil_image is not None:
            try:
                img = ImageQt.ImageQt(pil_image)
            except AttributeError as e:
                img = None
            except IsADirectoryError as e:
                img = None
            except Exception as e:
                img = None
            self.image = img
        else:
            self.image = QImage(
                self.application_settings.working_width,
                self.application_settings.working_height,
                QImage.Format.Format_ARGB32,
            )
            self.image.fill(Qt.GlobalColor.transparent)

    def set_item(
        self,
        image: QImage = None,
        z_index: int = 5,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ):
        self.setSceneRect(self._extended_viewport_rect)

        if image is not None:
            x = self.active_grid_settings.pos_x if x is None else x
            y = self.active_grid_settings.pos_y if y is None else y

            # Check if we have layer items - if so, don't use the old drawing pad item system
            if len(self._layer_items) > 0:
                logger.debug(
                    "Layer system active, skipping drawing pad item creation"
                )
                return

            if self.item is None:
                self.item = LayerImageItem(image)
                if self.item.scene() is None:
                    self.addItem(self.item)
                    self.item.setPos(x, y)
                    self.original_item_positions[self.item] = self.item.pos()
            else:
                self.item.setPos(x, y)
                self.original_item_positions[self.item] = self.item.pos()
                if image is not None and not image.isNull():
                    try:
                        self.item.updateImage(image)
                    except Exception:
                        if hasattr(self, "logger"):
                            self.logger.warning(
                                "Failed to update existing item with new image."
                            )
            self.item.setZValue(z_index)

            self.item.setVisible(True)

    def clear_selection(self):
        self.selection_start_pos = None

    def clear_selection(self):
        self.selection_start_pos = None
        self.selection_stop_pos = None

    def initialize_image(self, image: Image = None, generated: bool = False):
        self.stop_painter()
        self.set_image(image)

        if generated:
            self.update_drawing_pad_settings(
                x_pos=self.active_grid_settings.pos_x,
                y_pos=self.active_grid_settings.pos_y,
            )
            x = self.active_grid_settings.pos_x
            y = self.active_grid_settings.pos_y
        else:
            x = self.drawing_pad_settings.x_pos
            y = self.drawing_pad_settings.y_pos

        self.set_item(self.image, x=x, y=y)
        self.set_painter(self.image)

        # Initialize layers on first image initialization
        if not self._layers_initialized:
            self._layers_initialized = True
            self._refresh_layer_display()

        self.update()
        for view in self.views():
            view.viewport().update()
            view.update()
        self.update_image_position(self.get_canvas_offset())

    def stop_painter(self):
        if self.painter is not None and self.painter.isActive():
            self.painter.end()

    def set_painter(self, image: QImage):
        if image is None:
            return
        try:
            # Ensure any existing painter is stopped first
            if self.painter and self.painter.isActive():
                self.painter.end()
            self.painter = QPainter(image)
        except TypeError as _e:
            pass

    def _update_current_settings(self, key, value):
        if self.settings_key == "controlnet_settings":
            self.update_controlnet_settings(**{key: value})
        elif self.settings_key == "image_to_image_settings":
            self.update_image_to_image_settings(**{key: value})
        elif self.settings_key == "outpaint_settings":
            self.update_outpaint_settings(**{key: value})
        elif self.settings_key == "drawing_pad_settings":
            self.update_drawing_pad_settings(**{key: value})

    def _load_image_from_object(self, image: Image, is_outpaint: bool = False):
        self._add_image_to_scene(is_outpaint=is_outpaint, image=image)

    def _load_image_from_url_or_file(
        self, url_or_path: str
    ) -> Optional[Image.Image]:
        """Load an image from a local file or HTTP(S) URL."""
        if url_or_path.startswith("http://") or url_or_path.startswith(
            "https://"
        ):
            try:
                resp = requests.get(url_or_path, timeout=10)
                resp.raise_for_status()
                return Image.open(io.BytesIO(resp.content)).convert("RGBA")
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.error(f"Failed to download image: {e}")
                return None
        elif url_or_path.startswith("file://"):
            path = url_or_path[7:]
            if os.path.exists(path):
                try:
                    return Image.open(path).convert("RGBA")
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.error(f"Failed to open file image: {e}")
            return None
        else:
            if os.path.exists(url_or_path):
                try:
                    return Image.open(url_or_path).convert("RGBA")
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.error(f"Failed to open file image: {e}")
            return None

    def _paste_image_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        if hasattr(self, "logger"):
            self.logger.debug(f"Clipboard mime types: {mime.formats()}")
        # Try image data first
        if mime.hasImage():
            qimg = clipboard.image()
            if not qimg.isNull():
                buffer = QImage(qimg)
                ptr = buffer.bits()
                ptr.setsize(buffer.sizeInBytes())
                img = Image.frombuffer(
                    "RGBA",
                    (buffer.width(), buffer.height()),
                    bytes(ptr),
                    "raw",
                    "BGRA",
                )
                return img
        # Try raw image data (e.g. 'image/png') with both .data() and bytes()
        for fmt in mime.formats():
            if fmt.startswith("image/"):
                data = mime.data(fmt)
                # Try PyQt6/PySide6 QByteArray .data() and bytes()
                for get_bytes in (lambda d: d.data(), bytes):
                    try:
                        # Validate data before opening
                        data_bytes = get_bytes(data)
                        if not data_bytes or len(data_bytes) < 10:
                            continue
                        img = Image.open(io.BytesIO(data_bytes))
                        # Verify the image can be loaded
                        img.verify()
                        # Reopen since verify() consumes the image
                        img = Image.open(io.BytesIO(data_bytes))
                        if hasattr(self, "logger"):
                            self.logger.debug(
                                f"Loaded image from clipboard mime {fmt} using {get_bytes.__name__}"
                            )
                        return img
                    except Exception as e:
                        if hasattr(self, "logger"):
                            self.logger.error(
                                f"Failed to load image from clipboard mime {fmt} using {get_bytes.__name__}: {e}"
                            )
        # Try URLs (e.g., from browser)
        if mime.hasUrls():
            for url in mime.urls():
                url_str = url.toString()
                img = self._load_image_from_url_or_file(url_str)
                if img is not None:
                    return img
        # Try text (sometimes browsers put image URL as text)
        if mime.hasText():
            text = mime.text()
            if (
                text.startswith("http://")
                or text.startswith("https://")
                or text.startswith("file://")
            ):
                img = self._load_image_from_url_or_file(text)
                if img is not None:
                    return img
        if hasattr(self, "logger"):
            self.logger.warning("No image found in clipboard for paste.")
        return None

    def _copy_image(self, image: Image) -> Image:
        return self._move_pixmap_to_clipboard(image)

    def _move_pixmap_to_clipboard(self, image: Image) -> Image:
        if image is None:
            self.logger.warning("No image to copy to clipboard.")
            return None
        if not isinstance(image, Image.Image):
            self.logger.warning("Invalid image type.")
            return None
        data = io.BytesIO()
        image.save(data, format="png")
        data = data.getvalue()
        try:
            subprocess.Popen(
                ["xclip", "-selection", "clipboard", "-t", "image/png"],
                stdin=subprocess.PIPE,
            ).communicate(data)
        except FileNotFoundError:
            self.logger.error(
                "xclip not found. Cannot copy image to clipboard."
            )
            pass
        return image

    @profile
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

    def _resize_image(self, image: Image) -> Image:
        if image is None:
            return

        max_size = (
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        image.thumbnail(max_size, PIL.Image.Resampling.BICUBIC)
        return image

    @profile
    def _add_image_to_scene(
        self,
        image: Image.Image,
        is_outpaint: bool = False,
        outpaint_box_rect: Optional[Rect] = None,
        generated: bool = False,
    ):
        if image is None:
            return
        # NOTE: Major hotspot previously (line profiler ~44% time) was the
        # second attribute access to drawing_pad_settings.* which triggered
        # another full settings DB load. Cache the settings object locally
        # so we only hit the database once for both x_pos/y_pos.
        canvas_offset = self.get_canvas_offset()
        try:
            settings = self.drawing_pad_settings  # single DB fetch
            settings_x = settings.x_pos
            settings_y = settings.y_pos
        except Exception as e:
            self.logger.warning(
                f"Error accessing drawing pad settings: {e}, using defaults"
            )
            settings_x = 0
            settings_y = 0

        if outpaint_box_rect:
            if is_outpaint:
                image, root_point, _pivot_point = self._handle_outpaint(
                    outpaint_box_rect, image
                )
            else:
                root_point = QPoint(outpaint_box_rect.x, outpaint_box_rect.y)
        elif settings_x is not None and settings_y is not None:
            root_point = QPoint(settings_x, settings_y)
        else:
            root_point = QPoint(0, 0)

        # If generated, prefer active_rect from active grid settings for precise placement
        if generated:
            try:
                # Cache active grid settings to avoid multiple DB queries (expire after 1 second)
                current_time = time.time()
                if (
                    self._active_grid_cache is None
                    or current_time - self._active_grid_cache_time > 1.0
                ):
                    self._active_grid_cache = self.active_grid_settings
                    self._active_grid_cache_time = current_time

                active_grid = self._active_grid_cache
                root_point = QPoint(
                    active_grid.pos_x,
                    active_grid.pos_y,
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to use active grid settings position: {e}"
                )

        # Avoid double ImageQt conversions: initialize_image will convert.
        # If an item already exists we still need a QImage for updateImage,
        # otherwise we can let initialize_image handle creation.
        q_image = None
        if self.item:
            # Converting PIL image to QImage for existing item
            try:
                # Enhanced caching with image content hash to detect actual changes
                image_hash = (
                    hash(image.tobytes())
                    if hasattr(image, "tobytes")
                    else id(image)
                )
                cache_valid = (
                    self._qimage_cache is not None
                    and self._qimage_cache_size == image.size
                    and hasattr(self, "_qimage_cache_hash")
                    and self._qimage_cache_hash == image_hash
                    and not self._qimage_cache.isNull()
                )

                if cache_valid:
                    # Using cached QImage
                    q_image = self._qimage_cache
                else:
                    # Optimize: Use direct QImage creation instead of ImageQt for better performance
                    if image.mode == "RGBA":
                        # Direct RGBA conversion - fastest path
                        w, h = image.size
                        img_data = image.tobytes("raw", "RGBA")
                        q_image = QImage(
                            img_data, w, h, QImage.Format.Format_RGBA8888
                        )
                    elif image.mode == "RGB":
                        # Direct RGB conversion
                        w, h = image.size
                        img_data = image.tobytes("raw", "RGB")
                        q_image = QImage(
                            img_data, w, h, QImage.Format.Format_RGB888
                        )
                    else:
                        # Fallback to RGBA conversion + direct creation
                        rgba_image = image.convert("RGBA")
                        w, h = rgba_image.size
                        img_data = rgba_image.tobytes("raw", "RGBA")
                        q_image = QImage(
                            img_data, w, h, QImage.Format.Format_RGBA8888
                        )

                    # Cache the result
                    self._qimage_cache = q_image
                    self._qimage_cache_size = image.size
                    self._qimage_cache_hash = image_hash
            except Exception as e:
                self.logger.error(f"Failed to convert image to QImage: {e}")
                try:
                    rgba_image = image.convert("RGBA")
                    q_image = ImageQt.ImageQt(rgba_image)
                except Exception as e2:
                    self.logger.error(f"Retry RGBA conversion failed: {e2}")
                    q_image = None
            if q_image is not None and not q_image.isNull():
                try:
                    # Stop any active painter before updating the image
                    if self.painter and self.painter.isActive():
                        self.painter.end()

                    self.item.updateImage(q_image)
                    # CRITICAL: Update self.image so drawing operations work on the correct image
                    self.image = q_image

                    # Restart painter with new image
                    self.set_painter(self.image)
                except Exception:
                    pass
                self.item.setZValue(0)
            else:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        "Skipped updateImage due to null QImage (possible decode failure)."
                    )
        else:
            # Defer item creation to initialize_image for consistency.
            pass

        if self.item:
            absolute_pos = QPointF(root_point.x(), root_point.y())
            self.original_item_positions[self.item] = absolute_pos

            visible_pos_x = absolute_pos.x() - canvas_offset.x()
            visible_pos_y = absolute_pos.y() - canvas_offset.y()
            current_pos = self.item.pos()
            if (
                abs(current_pos.x() - visible_pos_x) > 0.5
                or abs(current_pos.y() - visible_pos_y) > 0.5
            ):
                self.item.setPos(visible_pos_x, visible_pos_y)

        # For new items we need full initialization.
        if not self.item:
            self.current_active_image = image
            self.initialize_image(image, generated=generated)
            if self.item:
                self.original_item_positions[self.item] = QPointF(
                    root_point.x(), root_point.y()
                )
                self.update_image_position(self.get_canvas_offset())
            self.update()
            return

        # Existing item: avoid full initialize_image (expensive duplicate work)
        # Optimize: Only update current_active_image if it's actually different
        if self.current_active_image is not image:
            self.current_active_image = image
        # If conversion pipeline produced a null cached qimage previously, re-attempt a safe RGBA conversion
        if self.item and (
            self._qimage_cache is None or self._qimage_cache.isNull()
        ):
            try:
                safe_rgba = (
                    image if image.mode == "RGBA" else image.convert("RGBA")
                )
                # Use our optimized direct QImage creation instead of ImageQt
                w, h = safe_rgba.size
                img_data = safe_rgba.tobytes("raw", "RGBA")
                q_image_retry = QImage(
                    img_data, w, h, QImage.Format.Format_RGBA8888
                )

                if not q_image_retry.isNull():
                    self._qimage_cache = q_image_retry
                    self._qimage_cache_size = safe_rgba.size
                    try:
                        # Stop any active painter before updating the image
                        if self.painter and self.painter.isActive():
                            self.painter.end()

                        self.item.updateImage(q_image_retry)
                        # CRITICAL: Update self.image so drawing operations work on the correct image
                        self.image = q_image_retry

                        # Restart painter with new image
                        self.set_painter(self.image)
                    except Exception:
                        pass
            except Exception:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        "Retry RGBA->QImage failed; image update skipped."
                    )
        # Update stored absolute origin then reposition
        self.original_item_positions[self.item] = QPointF(
            root_point.x(), root_point.y()
        )
        self.update_image_position(self.get_canvas_offset())
        self.update()

    def _handle_outpaint(
        self, outpaint_box_rect: Rect, outpainted_image: Image
    ) -> Tuple[Image.Image, QPoint, QPoint]:
        if self.current_active_image is None:
            point = QPoint(outpaint_box_rect.x, outpaint_box_rect.y)
            return outpainted_image, QPoint(0, 0), point

        existing_image_copy = self.current_active_image.copy()
        width = existing_image_copy.width
        height = existing_image_copy.height

        pivot_point = self.image_pivot_point
        root_point = QPoint(0, 0)
        current_image_position = QPoint(0, 0)

        is_drawing_left = outpaint_box_rect.x < current_image_position.x()
        is_drawing_right = outpaint_box_rect.x > current_image_position.x()
        is_drawing_up = outpaint_box_rect.y < current_image_position.y()
        is_drawing_down = outpaint_box_rect.y > current_image_position.y()

        x_pos = outpaint_box_rect.x
        y_pos = outpaint_box_rect.y
        outpaint_width = outpaint_box_rect.width
        outpaint_height = outpaint_box_rect.height

        if is_drawing_right:
            if x_pos + outpaint_width > width:
                width = x_pos + outpaint_width

        if is_drawing_down:
            if y_pos + outpaint_height > height:
                height = y_pos + outpaint_height

        if is_drawing_up:
            height += current_image_position.y()
            root_point.setY(outpaint_box_rect.y)

        if is_drawing_left:
            width += current_image_position.x()
            root_point.setX(outpaint_box_rect.x)

        new_dimensions = (width, height)

        new_image = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_a = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_b = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))

        image_root_point = QPoint(root_point.x(), root_point.y())
        image_pivot_point = QPoint(pivot_point.x(), pivot_point.y())

        new_image_a.paste(
            outpainted_image,
            (int(outpaint_box_rect.x), int(outpaint_box_rect.y())),
        )
        new_image_b.paste(
            existing_image_copy,
            (current_image_position.x(), current_image_position.y()),
        )

        mask_image = self.drawing_pad_mask
        mask = mask_image.convert("L").point(lambda p: p > 128 and 255)
        inverted_mask = Image.eval(mask, lambda p: 255 - p)
        pos_x = outpaint_box_rect.x
        pos_y = outpaint_box_rect.y
        if pos_x < 0:
            pos_x = 0
        if pos_y < 0:
            pos_y = 0
        new_mask = Image.new("L", new_dimensions, 255)
        new_mask.paste(inverted_mask, (pos_x, pos_y))
        new_image_b = Image.composite(
            new_image_b, Image.new("RGBA", new_image_b.size), new_mask
        )

        new_image = Image.alpha_composite(new_image, new_image_a)
        new_image = Image.alpha_composite(new_image, new_image_b)

        return new_image, image_root_point, image_pivot_point

    def _set_current_active_image(self, image: Image):
        self.initialize_image(image)

    def _rotate_90_clockwise(self):
        self.rotate_image(-90)

    def _rotate_90_counterclockwise(self):
        self.rotate_image(90)

    def rotate_image(self, angle: float):
        image = self.current_active_image
        if image is not None:
            self._add_image_to_undo()
            image = image.rotate(angle, expand=True)
            self.current_active_image = image
            self.initialize_image(image)

    def _add_undo_history(self, data: Dict):
        self.undo_history.append(data)

    def _add_redo_history(self, data: Dict):
        self.redo_history.append(data)

    def _clear_history(self):
        self.undo_history = []
        self.redo_history = []
        self.api.art.canvas.clear_history()

    def _cut_image(self, image: Image = None) -> Image:
        image = self._copy_image(image)
        if image is not None:
            self._add_image_to_undo(image)
            self.delete_image()

    def _add_image_to_undo(self, image: Image = None):
        if image is None:
            # Use cached reference first to avoid database lookup during pending persistence
            image = self._current_active_image_ref
            if image is None:
                # Fallback to property getter if no cached reference
                image = self.current_active_image
        self._add_undo_history({"image": image if image is not None else None})
        self.api.art.canvas.update_history(
            len(self.undo_history), len(self.redo_history)
        )

    def _add_image_to_redo(self):
        # Use cached reference first to avoid database lookup during pending persistence
        image = self._current_active_image_ref
        if image is None:
            # Fallback to property getter if no cached reference
            image = self.current_active_image
        self._add_redo_history({"image": image if image is not None else None})
        self.api.art.canvas.update_history(
            len(self.undo_history), len(self.redo_history)
        )

    def _handle_left_mouse_press(self, event):
        try:
            self.start_pos = event.scenePos()
        except AttributeError:
            pass

    def _handle_left_mouse_release(self, event):
        pass

    def _handle_cursor(self, event, apply_cursor: bool = True):
        if hasattr(self, "_last_cursor_state"):
            current_state = (event.type(), apply_cursor)
            if self._last_cursor_state == current_state:
                return
        self._last_cursor_state = (event.type(), apply_cursor)
        evt = event
        if not hasattr(event, "button"):

            class SimpleEvent:
                def __init__(self, original_event):
                    self.type_value = original_event.type()
                    self.button_value = None
                    self.buttons_value = Qt.MouseButton.NoButton

                def type(self):
                    return self.type_value

                def button(self):
                    return self.button_value

                def buttons(self):
                    return self.buttons_value

            evt = SimpleEvent(event)
        if self.api and hasattr(self.api, "art") and self.api.art:
            self.api.art.canvas.update_cursor(evt, apply_cursor)

    @staticmethod
    def _load_image(image_path: str) -> Image:
        image = Image.open(image_path)
        return image

    def _apply_filter(self, _filter_object: ImageFilter.Filter):
        if self.settings_key != "drawing_pad_settings":
            return
        self._add_image_to_undo(self.image_backup)
        self.previewing_filter = False
        self.image_backup = None

    def _cancel_filter(self) -> Image:
        image = None
        if self.image_backup:
            image = self.image_backup.copy()
            self.image_backup = None
        self.previewing_filter = False
        return image

    def _preview_filter(self, image: Image, filter_object: ImageFilter.Filter):
        if self.settings_key != "drawing_pad_settings":
            return
        if not image:
            return
        if not self.previewing_filter:
            self.image_backup = image.copy()
            self.previewing_filter = True
        else:
            image = self.image_backup.copy()
        filtered_image = filter_object.filter(image)
        return filtered_image

    def update_image_position(self, canvas_offset):
        # Update the old drawing pad item if it exists
        if self.item:
            if self.item not in self.original_item_positions:
                abs_x = self.drawing_pad_settings.x_pos
                abs_y = self.drawing_pad_settings.y_pos

                if abs_x is None or abs_y is None:
                    abs_x = self.item.pos().x()
                    abs_y = self.item.pos().y()

                self.original_item_positions[self.item] = QPointF(abs_x, abs_y)

            original_pos = self.original_item_positions[self.item]

            new_x = original_pos.x() - canvas_offset.x()
            new_y = original_pos.y() - canvas_offset.y()

            current_pos = self.item.pos()
            if (
                abs(current_pos.x() - new_x) > 1
                or abs(current_pos.y() - new_y) > 1
            ):
                self.item.prepareGeometryChange()
                self.item.setPos(new_x, new_y)
                self.item.setVisible(True)
                rect = self.item.boundingRect().adjusted(-10, -10, 10, 10)
                scene_rect = self.item.mapRectToScene(rect)
                self.update(scene_rect)

        # Update layer items
        from airunner.components.art.data.canvas_layer import CanvasLayer
        from airunner.components.art.data.drawingpad_settings import (
            DrawingPadSettings,
        )

        for layer_id, layer_item in self._layer_items.items():
            # Get the original position from DrawingPadSettings
            if layer_item not in self.original_item_positions:
                try:
                    results = DrawingPadSettings.objects.filter_by(
                        layer_id=layer_id
                    )
                    settings = results[0] if results else None
                    if settings:
                        abs_x = settings.x_pos or 0
                        abs_y = settings.y_pos or 0
                    else:
                        abs_x = layer_item.pos().x()
                        abs_y = layer_item.pos().y()

                    self.original_item_positions[layer_item] = QPointF(
                        abs_x, abs_y
                    )
                except Exception as e:
                    # Fallback to current position
                    self.original_item_positions[layer_item] = layer_item.pos()

            original_pos = self.original_item_positions[layer_item]
            new_x = original_pos.x() - canvas_offset.x()
            new_y = original_pos.y() - canvas_offset.y()

            current_pos = layer_item.pos()
            if (
                abs(current_pos.x() - new_x) > 1
                or abs(current_pos.y() - new_y) > 1
            ):
                layer_item.prepareGeometryChange()
                layer_item.setPos(new_x, new_y)
                layer_item.setVisible(
                    layer_item.isVisible()
                )  # Preserve visibility
                rect = layer_item.boundingRect().adjusted(-10, -10, 10, 10)
                scene_rect = layer_item.mapRectToScene(rect)
                self.update(scene_rect)

    def get_canvas_offset(self):
        if self.views() and hasattr(self.views()[0], "canvas_offset"):
            return self.views()[0].canvas_offset
        return QPointF(0, 0)
