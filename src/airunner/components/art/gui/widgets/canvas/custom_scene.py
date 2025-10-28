import io
import math
import os
import subprocess
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, is_dataclass
from typing import Optional, Tuple, Dict, Any, Iterable, List

import PIL
from PIL import ImageQt, Image, ImageFilter
from PySide6.QtGui import QImage
from PySide6.QtCore import Qt, QPoint, QRect, QPointF, QMetaObject, Slot, Q_ARG
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
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.data.session_manager import session_scope
from airunner.components.model_management import (
    ModelResourceManager,
    CanvasMemoryTracker,
)

import requests  # Added for HTTP(S) image download

from airunner.enums import SignalCode, CanvasToolName, EngineResponseCode
from airunner.components.art.gui.widgets.canvas.mixins import (
    CanvasFilterMixin,
    CanvasTransformMixin,
    CanvasDragDropMixin,
    CanvasClipboardMixin,
    CanvasLayerMixin,
    CanvasHistoryMixin,
    CanvasPersistenceMixin,
    CanvasGenerationMixin,
)
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
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
from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.utils.image_filter_utils import (
    build_filter_object_from_model,
)


_PERSIST_EXECUTOR = ThreadPoolExecutor(max_workers=1)

_SETTINGS_PERSISTENCE_MAP: Dict[str, Tuple[type, bool]] = {
    "drawing_pad_settings": (DrawingPadSettings, True),
    "controlnet_settings": (ControlnetSettings, True),
    "image_to_image_settings": (ImageToImageSettings, True),
    "outpaint_settings": (OutpaintSettings, True),
}


def _persist_image_worker(
    settings_key: str,
    layer_id: Optional[int],
    column_name: str,
    pil_image: Optional[Image.Image],
    binary_data: Optional[bytes],
    raw_storage_enabled: bool,
    generation: int,
) -> Dict[str, Any]:
    model_entry = _SETTINGS_PERSISTENCE_MAP.get(settings_key)
    if model_entry is None:
        return {
            "error": f"unsupported_settings_key:{settings_key}",
            "generation": generation,
        }

    model_class, layer_scoped = model_entry
    image_binary = binary_data

    if image_binary is None and pil_image is not None:
        try:
            if raw_storage_enabled:
                rgba_image = (
                    pil_image
                    if pil_image.mode == "RGBA"
                    else pil_image.convert("RGBA")
                )
                width, height = rgba_image.size
                header = (
                    b"AIRAW1"
                    + width.to_bytes(4, "big")
                    + height.to_bytes(4, "big")
                )
                image_binary = header + rgba_image.tobytes()
            else:
                image_binary = convert_image_to_binary(pil_image)
        except Exception:
            try:
                image_binary = convert_image_to_binary(
                    pil_image.convert("RGBA")
                )
            except Exception as exc:
                return {
                    "error": f"image_conversion_failed:{exc}",
                    "generation": generation,
                }

    if image_binary is None:
        return {"error": "empty_binary", "generation": generation}

    try:
        with session_scope() as session:
            if layer_scoped:
                query = session.query(model_class)
                if layer_id is not None:
                    query = query.filter(model_class.layer_id == layer_id)
                setting = query.first()
                if setting is None:
                    setting = model_class(layer_id=layer_id)
                    session.add(setting)
                setattr(setting, column_name, image_binary)
            else:
                setting = (
                    session.query(model_class)
                    .order_by(model_class.id.desc())
                    .first()
                )
                if setting is None:
                    setting = model_class()
                    session.add(setting)
                setattr(setting, column_name, image_binary)
    except Exception as exc:
        return {"error": f"db_error:{exc}", "generation": generation}

    return {
        "generation": generation,
        "table_name": model_class.__tablename__,
        "column_name": column_name,
        "binary": image_binary,
        "settings_key": settings_key,
        "layer_id": layer_id,
    }


def _dispatch_persist_result(scene_ref, future):
    scene = scene_ref()
    if scene is None:
        return
    try:
        payload = future.result()
    except Exception as exc:  # pragma: no cover - defensive
        payload = {"error": f"worker_exception:{exc}", "generation": 0}

    QMetaObject.invokeMethod(
        scene,
        "_handle_persist_result",
        Qt.QueuedConnection,
        Q_ARG(object, payload),
    )


class CustomScene(
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
        self._painter_target = None
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
        self._history_transactions: Dict[int | None, Dict[str, Any]] = {}
        self._structure_history_transaction: Optional[Dict[str, Any]] = None
        self.right_mouse_button_pressed = False
        self.handling_event = False
        self._original_item_positions = {}  # Store original positions of items
        # Debounce timer for persisting current_active_image to DB
        self._persist_timer = QTimer()
        self._persist_timer.setSingleShot(True)
        self._persist_timer.timeout.connect(self._flush_pending_image)
        self._pending_image_binary = None
        self._pending_image_ref = None  # defer heavy conversion to flush
        self._persist_delay_ms = 1000
        self._active_persist_future = None
        self._persist_generation = 0
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
        # Track user interaction state to avoid blocking UI while drawing/panning
        self._is_user_interacting = False

        # Flag to prevent refresh during drag operations
        self.is_dragging = False

        # Add viewport rectangle that includes negative space
        self._extended_viewport_rect = QRect(-2000, -2000, 4000, 4000)

        # Layer rendering system
        self._layer_items = (
            {}
        )  # Maps layer_id to LayerImageItem graphics items
        self._layers_initialized = False

        # Dynamic canvas growth settings
        self._surface_growth_step = 128
        self._minimum_surface_size = 128

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
                SignalCode.LAYER_SELECTION_CHANGED,
                self._on_layer_selection_changed,
            ),
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
            (
                SignalCode.LAYER_OPERATION_BEGIN,
                self.on_layer_operation_begin,
            ),
            (
                SignalCode.LAYER_OPERATION_COMMIT,
                self.on_layer_operation_commit,
            ),
            (
                SignalCode.LAYER_OPERATION_CANCEL,
                self.on_layer_operation_cancel,
            ),
        ]:
            self.register(signal, handler)

    @property
    def original_item_positions(self) -> Dict[str, QPointF]:
        """Returns the original positions of items in the scene."""
        return self._original_item_positions

    @original_item_positions.setter
    def original_item_positions(self, value: Dict[str, QPointF]):
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
        """Set the current active image and schedule a debounced persist.

        Heavy work (converting to bytes and writing to DB) is deferred to
        a QTimer tick to keep the UI responsive immediately after image load.
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

        # Check lock before persisting any changes
        if getattr(self.current_settings, "lock_input_image", False):
            # User has locked the input image; do not persist changes
            # Still update in-memory reference for display but skip DB write
            self._current_active_image_ref = image
            return

        # Fast identity check: same object reference -> skip
        if image is self._current_active_image_ref:
            return
        # Update in-memory ref; binary will be produced during flush
        self._current_active_image_ref = image
        self._current_active_image_binary = None
        self._pending_image_ref = image
        self._pending_image_binary = None

        # Restart timer with configured debounce window
        self._persist_timer.start(self._persist_delay_ms)

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
            # Auto-apply filters flagged in the DB. These filters are applied
            # to the canvas via the existing image_filter service.
            try:
                auto_filters = (
                    ImageFilter.objects.filter_by(auto_apply=True) or []
                )
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
        else:
            if self.settings_key == "drawing_pad_settings":
                pass

        if self.settings_key == "drawing_pad_settings":
            if callback:
                callback(data)
            self.api.art.stop_progress_bar()

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

    def _capture_layers_state(
        self, layer_ids: Iterable[int]
    ) -> List[Dict[str, Any]]:
        snapshots: List[Dict[str, Any]] = []
        for layer_id in layer_ids:
            layer_record = self._serialize_record(
                CanvasLayer.objects.get(layer_id)
            )
            if layer_record is None:
                continue
            snapshot: Dict[str, Any] = {"layer": layer_record}
            snapshot["drawing_pad"] = self._serialize_record(
                DrawingPadSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["controlnet"] = self._serialize_record(
                ControlnetSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["image_to_image"] = self._serialize_record(
                ImageToImageSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["outpaint"] = self._serialize_record(
                OutpaintSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["brush"] = self._serialize_record(
                BrushSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshot["metadata"] = self._serialize_record(
                MetadataSettings.objects.filter_by_first(layer_id=layer_id)
            )
            snapshots.append(snapshot)
        return snapshots

    def _merge_model_from_dict(self, model_cls, data: Dict[str, Any]) -> None:
        if not data:
            return
        try:
            model_instance = model_cls(**data)
            model_cls.objects.merge(model_instance)
        except Exception as exc:
            if hasattr(self, "logger"):
                self.logger.error(
                    "Failed to merge %s for layer operation: %s",
                    model_cls.__name__,
                    exc,
                )

    def _restore_layers_from_snapshots(
        self, snapshots: List[Dict[str, Any]]
    ) -> None:
        for snapshot in snapshots:
            layer_data = snapshot.get("layer")
            if layer_data:
                self._merge_model_from_dict(CanvasLayer, layer_data)
            self._merge_model_from_dict(
                DrawingPadSettings, snapshot.get("drawing_pad") or {}
            )
            self._merge_model_from_dict(
                ControlnetSettings, snapshot.get("controlnet") or {}
            )
            self._merge_model_from_dict(
                ImageToImageSettings, snapshot.get("image_to_image") or {}
            )
            self._merge_model_from_dict(
                OutpaintSettings, snapshot.get("outpaint") or {}
            )
            self._merge_model_from_dict(
                BrushSettings, snapshot.get("brush") or {}
            )
            self._merge_model_from_dict(
                MetadataSettings, snapshot.get("metadata") or {}
            )

    def _remove_layers(self, layer_ids: Iterable[int]) -> None:
        for layer_id in list(layer_ids):
            layer_item = self._layer_items.pop(layer_id, None)
            if layer_item is not None and layer_item.scene():
                layer_item.scene().removeItem(layer_item)
            self._history_transactions.pop(layer_id, None)
            self._original_item_positions = {
                item: pos
                for item, pos in self._original_item_positions.items()
                if getattr(item, "layer_id", None) != layer_id
            }

            # Clear layer-specific cache entries to prevent stale data
            cache_by_key = (
                self.settings_mixin_shared_instance._settings_cache_by_key
            )
            for model_class in [
                DrawingPadSettings,
                ControlnetSettings,
                ImageToImageSettings,
                OutpaintSettings,
                BrushSettings,
                MetadataSettings,
            ]:
                cache_key = f"{model_class.__name__}_layer_{layer_id}"
                cache_by_key.pop(cache_key, None)

            DrawingPadSettings.objects.delete(layer_id=layer_id)
            ControlnetSettings.objects.delete(layer_id=layer_id)
            ImageToImageSettings.objects.delete(layer_id=layer_id)
            OutpaintSettings.objects.delete(layer_id=layer_id)

    def _apply_layer_orders(self, orders: List[Dict[str, int]]) -> None:
        for entry in orders:
            layer_id = entry.get("layer_id")
            order_value = entry.get("order")
            if layer_id is None or order_value is None:
                continue
            CanvasLayer.objects.update(layer_id, order=order_value)

    def _begin_layer_structure_transaction(
        self, action: str, layer_ids: Iterable[int]
    ) -> None:
        if not action:
            return
        self._structure_history_transaction = {
            "action": action,
            "layer_ids": list(layer_ids),
            "orders_before": self._capture_layer_orders(),
        }
        if action == "delete":
            self._structure_history_transaction["layers_before"] = (
                self._capture_layers_state(layer_ids)
            )

    def _commit_layer_structure_transaction(
        self, action: str, layer_ids: Iterable[int]
    ) -> None:
        if self._structure_history_transaction is None:
            return
        transaction = self._structure_history_transaction
        if transaction.get("action") != action:
            self._structure_history_transaction = None
            return

        resolved_layer_ids = list(layer_ids)
        if action == "create":
            transaction["layer_ids"] = resolved_layer_ids
        elif not resolved_layer_ids:
            resolved_layer_ids = list(transaction.get("layer_ids", []))

        orders_after = self._capture_layer_orders()
        entry: Dict[str, Any] = {
            "type": f"layer_{action}",
            "layer_ids": resolved_layer_ids,
            "orders_before": transaction.get("orders_before", []),
            "orders_after": orders_after,
        }

        if action == "create":
            entry["layers_after"] = self._capture_layers_state(
                resolved_layer_ids
            )
        elif action == "delete":
            entry["layers_before"] = transaction.get("layers_before", [])

        if action == "reorder" and (
            entry["orders_before"] == entry["orders_after"]
        ):
            self._structure_history_transaction = None
            return

        if action == "create" and not entry.get("layers_after"):
            self._structure_history_transaction = None
            return

        if action == "delete" and not entry.get("layers_before"):
            self._structure_history_transaction = None
            return

        self.undo_history.append(entry)
        self.redo_history.clear()
        self._structure_history_transaction = None
        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.update_history(
                len(self.undo_history), len(self.redo_history)
            )
        # Update canvas memory allocation in ModelResourceManager
        self._update_canvas_memory_allocation()

    def _update_canvas_memory_allocation(self):
        """Update ModelResourceManager with current canvas memory usage."""
        try:
            resource_manager = ModelResourceManager()
            tracker = CanvasMemoryTracker()

            # Estimate memory used by canvas history
            vram_gb, ram_gb = tracker.estimate_history_memory(self)

            # Update the resource manager
            resource_manager.update_canvas_history_allocation(vram_gb, ram_gb)

        except Exception as e:
            # Don't let canvas memory tracking errors break the canvas
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"Failed to update canvas memory allocation: {e}"
                )

    def _cancel_layer_structure_transaction(self) -> None:
        self._structure_history_transaction = None

    def _apply_layer_structure(
        self, entry: Dict[str, Any], target: str
    ) -> None:
        entry_type = entry.get("type")
        if entry_type not in {
            "layer_create",
            "layer_delete",
            "layer_reorder",
        }:
            return

        layer_ids = entry.get("layer_ids", [])
        orders = (
            entry.get("orders_before", [])
            if target == "before"
            else entry.get("orders_after", [])
        )

        if entry_type == "layer_create":
            if target == "before":
                self._remove_layers(layer_ids)
            else:
                self._restore_layers_from_snapshots(
                    entry.get("layers_after", [])
                )
        elif entry_type == "layer_delete":
            if target == "before":
                self._restore_layers_from_snapshots(
                    entry.get("layers_before", [])
                )
            else:
                self._remove_layers(layer_ids)
        elif entry_type == "layer_reorder":
            pass

        if orders:
            self._apply_layer_orders(orders)

        self._refresh_layer_display()
        self.api.art.canvas.show_layers()
        if self.api and hasattr(self.api, "art"):
            self.api.art.canvas.update_image_positions()

    def show_event(self):
        self.handle_cached_send_image_to_canvas()
        # if not self._image_initialized:
        #     self._image_initialized = True
        #     self.initialize_image()
        # if not self._layers_initialized:
        #     self._layers_initialized = True
        #     self._refresh_layer_display()

    def _release_painter_for_device(self, device: Optional[QImage]):
        if device is not None and device is self._painter_target:
            self.stop_painter()

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
        # Accessing Qt objects can raise RuntimeError if the underlying
        # C++ object was deleted elsewhere. Catch both AttributeError
        # and RuntimeError to be defensive and avoid crashes.
        item_scene = None
        try:
            if hasattr(self, "item") and self.item is not None:
                item_scene = self.item.scene()
        except (AttributeError, RuntimeError):
            item_scene = None

        if item_scene is not None:
            try:
                item_scene.removeItem(self.item)
            except (RuntimeError, AttributeError):
                # Item was deleted or invalid; ignore and continue
                pass
        self.initialize_image(image)
        view.setSceneRect(current_viewport_rect)

    def delete_image(self):
        # Safely remove the image item from the scene (if present)
        item_scene = None
        try:
            if hasattr(self, "item") and self.item is not None:
                item_scene = self.item.scene()
        except (AttributeError, RuntimeError):
            item_scene = None

        if item_scene is not None:
            try:
                item_scene.removeItem(self.item)
            except (RuntimeError, AttributeError):
                # If the C++ object has already been deleted, skip removal
                pass

        # Properly end and reset the painter so drawBackground can reinitialize
        self.stop_painter()
        self.current_active_image = None
        self.image = None
        if hasattr(self, "item") and self.item is not None:
            del self.item
        self.item = None

    def _create_blank_surface(
        self, width: Optional[int] = None, height: Optional[int] = None
    ) -> QImage:
        w = self._minimum_surface_size if width is None else max(1, width)
        h = self._minimum_surface_size if height is None else max(1, height)
        surface = QImage(w, h, QImage.Format.Format_ARGB32)
        surface.fill(Qt.GlobalColor.transparent)
        return surface

    def _quantize_growth(self, value: int) -> int:
        if value <= 0:
            return 0
        step = self._surface_growth_step
        return max(step, int(math.ceil(value / step) * step))

    def _persist_item_origin(self, item: DraggablePixmap, origin: QPointF):
        try:
            if isinstance(item, LayerImageItem) and item.layer_id is not None:
                self.update_drawing_pad_settings(
                    x_pos=int(origin.x()),
                    y_pos=int(origin.y()),
                    layer_id=item.layer_id,
                )
                if hasattr(item, "layer_image_data"):
                    item.layer_image_data["pos_x"] = int(origin.x())
                    item.layer_image_data["pos_y"] = int(origin.y())
            elif item is self.item:
                self.update_drawing_pad_settings(
                    x_pos=int(origin.x()),
                    y_pos=int(origin.y()),
                )
        except Exception as exc:
            if hasattr(self, "logger"):
                self.logger.warning(
                    f"Failed to persist item origin update: {exc}"
                )

    def _expand_item_surface(
        self,
        item: DraggablePixmap,
        grow_left: int,
        grow_top: int,
        grow_right: int,
        grow_bottom: int,
    ) -> bool:
        if not any([grow_left, grow_top, grow_right, grow_bottom]):
            return False

        qimage = getattr(item, "qimage", None)
        if qimage is None and item is self.item:
            qimage = self.image

        if qimage is None:
            return False

        new_width = qimage.width() + grow_left + grow_right
        new_height = qimage.height() + grow_top + grow_bottom
        if new_width <= 0 or new_height <= 0:
            return False

        # Ensure the new surface supports alpha so any added margins remain
        # transparent. Using the source image's format may pick a non-alpha
        # format (eg. RGB32) which results in opaque white/black padding.
        new_image = QImage(new_width, new_height, QImage.Format.Format_ARGB32)
        new_image.fill(Qt.GlobalColor.transparent)

        self.stop_painter()

        painter = QPainter(new_image)
        painter.drawImage(grow_left, grow_top, qimage)
        painter.end()

        if hasattr(item, "updateImage"):
            try:
                item.updateImage(new_image)
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        f"Failed to update item image during expansion: {e}"
                    )
                return False
        else:
            return False

        if item is self.item:
            self.image = new_image

        original_pos = self.original_item_positions.get(item)
        if original_pos is None:
            canvas_offset = self.get_canvas_offset()
            original_pos = item.pos() + canvas_offset
        new_origin = QPointF(
            original_pos.x() - grow_left, original_pos.y() - grow_top
        )
        # Record new origin and log expansion for debugging
        self.original_item_positions[item] = new_origin
        if hasattr(self, "logger"):
            try:
                old_w = qimage.width()
                old_h = qimage.height()
                self.logger.debug(
                    f"Expanded item (layer_id={getattr(item, 'layer_id', None)}) from {old_w}x{old_h} to {new_width}x{new_height} (L{grow_left},T{grow_top},R{grow_right},B{grow_bottom})"
                )
            except Exception:
                pass
        self._persist_item_origin(item, new_origin)

        canvas_offset = self.get_canvas_offset()
        display_pos = QPointF(
            new_origin.x() - canvas_offset.x(),
            new_origin.y() - canvas_offset.y(),
        )
        item.setPos(display_pos)

        # Clear caches that rely on stale dimensions
        self._qimage_cache = None
        self._qimage_cache_size = None
        self._qimage_cache_hash = None
        self._current_active_image_ref = None

        return True

    def _ensure_item_contains_scene_point(
        self, item: DraggablePixmap, scene_point: QPointF, radius: float
    ) -> bool:
        if item is None:
            return False
        if not hasattr(item, "mapFromScene"):
            return False

        qimage = getattr(item, "qimage", None)
        if qimage is None and item is self.item:
            qimage = self.image

        if qimage is None:
            return False

        local_point = item.mapFromScene(scene_point)
        radius = float(max(radius, 0.0))

        left_needed = self._quantize_growth(
            int(math.ceil(radius - local_point.x()))
        )
        top_needed = self._quantize_growth(
            int(math.ceil(radius - local_point.y()))
        )
        right_needed = self._quantize_growth(
            int(math.ceil(local_point.x() + radius - qimage.width()))
        )
        bottom_needed = self._quantize_growth(
            int(math.ceil(local_point.y() + radius - qimage.height()))
        )

        return self._expand_item_surface(
            item,
            max(0, left_needed),
            max(0, top_needed),
            max(0, right_needed),
            max(0, bottom_needed),
        )

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
            except AttributeError:
                pil_image = None
            except PIL.UnidentifiedImageError as e:
                pil_image = None
            except Exception:
                pil_image = None

        if pil_image is not None:
            try:
                img = ImageQt.ImageQt(pil_image)
            except AttributeError:
                img = None
            except IsADirectoryError:
                img = None
            except Exception:
                img = None
            self.image = img
        else:
            self.image = self._create_blank_surface()
            self._current_active_image_ref = None
            self._current_active_image_binary = None

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
        self.current_active_image = image
        self.set_image(image)

        x = self.active_grid_settings.pos_x
        y = self.active_grid_settings.pos_y

        self.update_drawing_pad_settings(
            x_pos=x,
            y_pos=y,
        )

        self.set_item(self.image, x=x, y=y)
        self.set_painter(self.image)

        # Initialize layers only for the main drawing pad scene
        if getattr(self, "canvas_type", None) == "drawing_pad":
            if not self._layers_initialized:
                self._layers_initialized = True
                self._refresh_layer_display()

        self.update()

        for view in self.views():
            view.viewport().update()
            view.update()
        self.update_image_position(self.get_canvas_offset())

    def stop_painter(self):
        if self.painter is not None:
            if self.painter.isActive():
                self.painter.end()
            self.painter = None
        self._painter_target = None

    def set_painter(self, image: QImage):
        if image is None:
            return
        try:
            # Ensure any existing painter is fully stopped before rebinding
            self.stop_painter()
            self.painter = QPainter(image)
            self._painter_target = image
        except TypeError:
            self.painter = None
            self._painter_target = None

    def _update_current_settings(self, key, value):
        if self.settings_key == "controlnet_settings":
            self.update_controlnet_settings(**{key: value})
        elif self.settings_key == "image_to_image_settings":
            self.update_image_to_image_settings(**{key: value})
        elif self.settings_key == "outpaint_settings":
            self.update_outpaint_settings(**{key: value})
        elif self.settings_key == "drawing_pad_settings":
            self.update_drawing_pad_settings(**{key: value})

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

        # Check lock before updating the visual display with generated images
        # (but allow user-initiated imports and pastes)
        if generated and getattr(
            self.current_settings, "lock_input_image", False
        ):
            # User has locked the input image; do not update the visual scene
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
                # Check if item is still valid before using it
                try:
                    if self.item is not None:
                        self.item.setZValue(0)
                except (RuntimeError, AttributeError):
                    # Item was deleted or is no longer valid
                    pass
            else:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        "Skipped updateImage due to null QImage (possible decode failure)."
                    )
        else:
            # Defer item creation to initialize_image for consistency.
            pass

        if self.item:
            try:
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
            except (RuntimeError, AttributeError):
                # Item was deleted or is no longer valid
                pass

        # For new items we need full initialization.
        if not self.item:
            self.current_active_image = image
            self.initialize_image(image, generated=generated)
            # if self.item:
            #     self.original_item_positions[self.item] = QPointF(
            #         root_point.x(), root_point.y()
            #     )
            #     self.update_image_position(self.get_canvas_offset())
            # self.update()
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
                    except (RuntimeError, AttributeError):
                        # Item was deleted or is no longer valid
                        pass
            except Exception:
                if hasattr(self, "logger"):
                    self.logger.warning(
                        "Retry RGBA->QImage failed; image update skipped."
                    )
        # Update stored absolute origin then reposition
        try:
            self.original_item_positions[self.item] = QPointF(
                root_point.x(), root_point.y()
            )
            self.update_image_position(self.get_canvas_offset())
        except (RuntimeError, AttributeError):
            # Item was deleted or is no longer valid
            pass
        self.update()

    def _set_current_active_image(self, image: Image):
        self.initialize_image(image)

    def _handle_left_mouse_press(self, event):
        try:
            self.start_pos = event.scenePos()
        except AttributeError:
            pass
        # Mark that user is interacting (drawing)
        self._persist_timer.stop()
        self._is_user_interacting = True

    def _handle_left_mouse_release(self, event):
        # Stroke finished; allow persistence after a short grace period
        self._is_user_interacting = False
        if (
            self._pending_image_ref is not None
            or self._pending_image_binary is not None
        ):
            self._persist_timer.start(self._persist_delay_ms)

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

    def update_image_position(
        self,
        canvas_offset,
        original_item_positions: Dict[str, QPointF] = None,
    ):
        from airunner.components.art.utils.canvas_position_manager import (
            CanvasPositionManager,
            ViewState,
        )

        original_item_positions = (
            self.original_item_positions
            if original_item_positions is None
            else original_item_positions
        )

        # Get view for grid compensation offset
        view = self.views()[0] if self.views() else None
        grid_compensation = (
            getattr(view, "_grid_compensation_offset", QPointF(0, 0))
            if view
            else QPointF(0, 0)
        )

        # Create position manager and view state
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=canvas_offset,
            grid_compensation=grid_compensation,
        )

        # Update the old drawing pad item if it exists
        if self.item:
            if self.item not in original_item_positions:
                abs_x = self.drawing_pad_settings.x_pos
                abs_y = self.drawing_pad_settings.y_pos

                if abs_x is None or abs_y is None:
                    abs_x = self.item.pos().x()
                    abs_y = self.item.pos().y()

                original_item_positions[self.item] = QPointF(abs_x, abs_y)

            original_pos = original_item_positions[self.item]

            # Use CanvasPositionManager for coordinate conversion
            display_pos = manager.absolute_to_display(original_pos, view_state)
            new_x = display_pos.x()
            new_y = display_pos.y()

            try:
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
            except (RuntimeError, AttributeError):
                # Item was deleted or is no longer valid
                pass

        # Create a copy of items to iterate over, as we might modify the dict
        layer_items_copy = list(self._layer_items.items())

        for layer_id, layer_item in layer_items_copy:
            try:
                if layer_item not in original_item_positions:
                    self.logger.info(
                        f"[UPDATE_POS] Layer {layer_id} item (id={id(layer_item)}) NOT in original_item_positions, reading from settings"
                    )
                    try:
                        drawing_pad_settings = (
                            self._get_layer_specific_settings(
                                DrawingPadSettings, layer_id=layer_id
                            )
                        )
                        if drawing_pad_settings:
                            abs_x = drawing_pad_settings.x_pos or 0
                            abs_y = drawing_pad_settings.y_pos or 0
                        else:
                            abs_x = layer_item.pos().x()
                            abs_y = layer_item.pos().y()

                        original_item_positions[layer_item] = QPointF(
                            abs_x, abs_y
                        )
                        self.logger.info(
                            f"[UPDATE_POS] Layer {layer_id}: read from settings x={abs_x}, y={abs_y}"
                        )
                    except Exception:
                        current_pos = layer_item.pos()
                        original_item_positions[layer_item] = current_pos
                else:
                    self.logger.info(
                        f"[UPDATE_POS] Layer {layer_id} item (id={id(layer_item)}) FOUND in original_item_positions"
                    )

                original_pos = original_item_positions[layer_item]
                self.logger.info(
                    f"[UPDATE_POS] Layer {layer_id}: using position x={original_pos.x()}, y={original_pos.y()}"
                )

                # Use CanvasPositionManager for coordinate conversion
                display_pos = manager.absolute_to_display(
                    original_pos, view_state
                )
                new_x = display_pos.x()
                new_y = display_pos.y()

                current_pos = layer_item.pos()
                if (
                    abs(current_pos.x() - new_x) > 1
                    or abs(current_pos.y() - new_y) > 1
                ):
                    layer_item.prepareGeometryChange()
                    layer_item.setPos(new_x, new_y)
                    layer_item.setVisible(layer_item.isVisible())
                    rect = layer_item.boundingRect().adjusted(-10, -10, 10, 10)
                    scene_rect = layer_item.mapRectToScene(rect)
                    self.update(scene_rect)

            except RuntimeError as e:
                if "Internal C++ object" in str(
                    e
                ) and "already deleted" in str(e):
                    self.logger.warning(
                        f"Layer item {layer_id} was already deleted during position update, removing from cache"
                    )
                    # Remove the invalid reference from our cache
                    if layer_id in self._layer_items:
                        del self._layer_items[layer_id]
                    # Also clean up original_item_positions if it exists
                    if layer_item in original_item_positions:
                        del original_item_positions[layer_item]
                else:
                    # Re-raise unexpected RuntimeErrors
                    raise
            except Exception as e:
                self.logger.warning(
                    f"Error updating position for layer {layer_id}: {e}"
                )
        self.original_item_positions = original_item_positions

    def get_canvas_offset(self):
        if self.views() and hasattr(self.views()[0], "canvas_offset"):
            return self.views()[0].canvas_offset
        return QPointF(0, 0)
