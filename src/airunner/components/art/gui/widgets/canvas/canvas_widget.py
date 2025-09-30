import base64
import json
from pathlib import Path

from PySide6.QtWidgets import QColorDialog
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QMessageBox
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, QPoint
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication

from airunner.gui.cursors.circle_brush import circle_cursor
from airunner.enums import SignalCode, CanvasToolName
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.canvas.templates.canvas_ui import (
    Ui_canvas,
)
from airunner.utils.widgets import load_splitter_settings
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner.components.art.data.controlnet_settings import (
    ControlnetSettings,
)
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.utils.widgets.save_splitter_settings import (
    save_splitter_settings,
)


class CanvasWidget(BaseWidget):
    """
    Widget responsible for multiple functionalities:

    - Allows the user to draw on a canvas.
    - Displays the grid.
    - Displays images.
    - Handles the active grid area.
    """

    widget_class_ = Ui_canvas
    icons = [
        ("file-plus", "new_button"),
        ("arrow-down", "import_button"),
        ("arrow-up", "export_button"),
        ("target", "recenter_button"),
        ("object-selected-icon", "active_grid_area_button"),
        ("pencil-icon", "brush_button"),
        ("eraser-icon", "eraser_button"),
        ("grid", "grid_button"),
        ("corner-up-left", "undo_button"),
        ("corner-up-right", "redo_button"),
        ("type", "text_button"),
        ("folder", "open_art_document"),
        ("save", "save_art_document"),
        ("link-2", "snap_to_grid_button"),
        ("move", "move_button"),
        ("message-square", "prompt_editor_button"),
        ("tool", "art_tools_button"),
    ]

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.ENABLE_BRUSH_TOOL_SIGNAL: lambda _message: self.on_brush_button_toggled(
                True
            ),
            SignalCode.ENABLE_ERASER_TOOL_SIGNAL: lambda _message: self.on_eraser_button_toggled(
                True
            ),
            SignalCode.ENABLE_MOVE_TOOL_SIGNAL: lambda _message: self.on_active_grid_area_button_toggled(
                True
            ),
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_toggle_tool_signal,
            SignalCode.TOGGLE_TOOL: self.on_toggle_tool_signal,
            SignalCode.TOGGLE_GRID: self.on_toggle_grid_signal,
            SignalCode.TOGGLE_GRID_SNAP: self.on_toggle_grid_snap_signal,
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
            SignalCode.CANVAS_UPDATE_GRID_INFO: self.update_grid_info,
            SignalCode.CANVAS_ZOOM_LEVEL_CHANGED: self.update_grid_info,
            SignalCode.SAVE_STATE: self.save_state,
        }
        self._initialized: bool = False
        self._splitters = ["splitter"]
        self._default_splitter_settings_applied = False
        super().__init__(*args, **kwargs)

        # Configure default splitter sizes for splitter
        # Assuming the main canvas area is the second panel (index 1)
        default_canvas_splitter_config = {
            "splitter": {"index_to_maximize": 1, "min_other_size": 50}
        }
        load_splitter_settings(
            self.ui,
            self._splitters,  # self._splitters is ["splitter"]
            default_maximize_config=default_canvas_splitter_config,
        )

        current_tool = self.current_tool
        show_grid = self.grid_settings.show_grid

        self._startPos = QPoint(0, 0)
        self.images = {}
        self.active_grid_area_pivot_point = QPoint(0, 0)
        self.active_grid_area_position = QPoint(0, 0)
        self.current_image_index = 0
        self.draggable_pixmaps_in_scene = {}
        self.drag_pos: QPoint = Optional[None]
        self._grid_settings = {}
        self._active_grid_settings = {}

        self.ui.grid_button.blockSignals(True)
        self.ui.snap_to_grid_button.blockSignals(True)
        self.ui.grid_button.setChecked(show_grid)
        self.ui.snap_to_grid_button.setChecked(self.grid_settings.snap_to_grid)
        self.ui.grid_button.blockSignals(False)
        self.ui.snap_to_grid_button.blockSignals(False)

        self.ui.splitter.splitterMoved.connect(self.on_splitter_changed_sizes)

        self.update_grid_info(
            {
                "offset_x": 0,
                "offset_y": 0,
            }
        )
        self._update_action_buttons(self.current_tool, True)

        self.set_button_color()

    _offset_x = 0
    _offset_y = 0

    @property
    def offset_x(self):
        return self._offset_x

    @offset_x.setter
    def offset_x(self, value):
        self._offset_x = value

    @property
    def offset_y(self):
        return self._offset_y

    @offset_y.setter
    def offset_y(self, value):
        self._offset_y = value

    def update_grid_info(self, data: Dict):
        self.offset_x = data.get("offset_x", self.offset_x)
        self.offset_y = data.get("offset_y", self.offset_y)
        zoom_level = round(self.grid_settings.zoom_level * 100, 2)
        self.ui.grid_info.setText(
            f"{self.offset_x}, {self.offset_y}, {zoom_level}%"
        )

    @property
    def current_tool(self):
        return (
            None
            if self.application_settings.current_tool is None
            else CanvasToolName(self.application_settings.current_tool)
        )

    @property
    def image_pivot_point(self):
        settings = self.application_settings
        try:
            return QPoint(settings.pivot_point_x, settings.pivot_point_y)
        except Exception as e:
            self.logger.error(e)
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        settings = self.application_settings
        settings.pivot_point_x = value.x()
        settings.pivot_point_y = value.y()
        self.update_application_settings(pivot_point_x=value.x())
        self.update_application_settings(pivot_point_y=value.y())

    @Slot(bool)
    def on_prompt_editor_button_clicked(self, val: bool):
        self._toggle_splitter_section(val, 0, self.ui.splitter)

    @Slot(bool)
    def on_art_tools_button_clicked(self, val: bool):
        self._toggle_splitter_section(val, 2, self.ui.splitter, 300)

    def on_splitter_changed_sizes(self):
        self.set_prompt_editor_button_checked()
        self.set_art_tools_button_checked()

    def set_prompt_editor_button_checked(self):
        self.ui.prompt_editor_button.blockSignals(True)
        self.ui.prompt_editor_button.setChecked(
            self.ui.splitter.sizes()[0] > 0
        )
        self.ui.prompt_editor_button.blockSignals(False)

    def set_art_tools_button_checked(self):
        self.ui.art_tools_button.blockSignals(True)
        self.ui.art_tools_button.setChecked(self.ui.splitter.sizes()[2] > 0)
        self.ui.art_tools_button.blockSignals(False)

    @Slot()
    def on_brush_color_button_clicked(self):
        self.color_button_clicked()

    @Slot(bool)
    def on_text_button_toggled(self, val: bool):
        self.api.art.canvas.toggle_tool(CanvasToolName.TEXT, val)

    @Slot()
    def on_recenter_button_clicked(self):
        self.api.art.canvas.recenter_grid()

    @Slot()
    def on_undo_button_clicked(self):
        self.api.art.canvas.undo()

    @Slot()
    def on_redo_button_clicked(self):
        self.api.art.canvas.redo()

    @Slot()
    def on_new_button_clicked(self):
        self._reset_canvas_document()

    @Slot(bool)
    def on_grid_button_toggled(self, val: bool):
        self.api.art.canvas.toggle_grid(val)

    @Slot(bool)
    def on_snap_to_grid_button_toggled(self, val: bool):
        self.api.art.canvas.toggle_grid_snap(val)

    @Slot()
    def on_import_button_clicked(self):
        self.api.art.canvas.import_image()

    @Slot()
    def on_export_button_clicked(self):
        self.api.art.canvas.export_image()

    @Slot()
    def on_open_art_document_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Document",
            "",
            "AI Runner Document (*.airunner)",
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            with path.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self._show_error_message(
                "Open Document Failed",
                f"Unable to open the selected document.\n\n{exc}",
            )
            if hasattr(self, "logger"):
                self.logger.exception(exc)
            return

        try:
            self._load_canvas_document(document)
        except Exception as exc:  # pragma: no cover - defensive UI feedback
            self._show_error_message(
                "Open Document Failed",
                "The document could not be loaded.",
            )
            if hasattr(self, "logger"):
                self.logger.exception(exc)

    @Slot()
    def on_save_art_document_clicked(self):
        document = self._serialize_canvas_document()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Document",
            "",
            "AI Runner Document (*.airunner)",
        )
        if not file_path:
            return

        path = Path(file_path)
        if path.suffix.lower() != ".airunner":
            path = path.with_suffix(".airunner")

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                json.dump(document, handle, indent=2)
        except Exception as exc:  # pragma: no cover - defensive UI feedback
            self._show_error_message(
                "Save Document Failed",
                f"Unable to save the document.\n\n{exc}",
            )
            if hasattr(self, "logger"):
                self.logger.exception(exc)

    @Slot(bool)
    def on_brush_button_toggled(self, val: bool):
        print("ON BRUSH BUTTON TOGGLED")
        self.api.art.canvas.toggle_tool(CanvasToolName.BRUSH, val)

    @Slot(bool)
    def on_eraser_button_toggled(self, val: bool):
        self.api.art.canvas.toggle_tool(CanvasToolName.ERASER, val)

    @Slot(bool)
    def on_active_grid_area_button_toggled(self, val: bool):
        self.api.art.canvas.toggle_tool(CanvasToolName.ACTIVE_GRID_AREA, val)

    @Slot(bool)
    def on_move_button_toggled(self, val: bool):
        self.api.art.canvas.toggle_tool(CanvasToolName.MOVE, val)

    def on_toggle_tool_signal(self, message: Dict):
        tool = message.get("tool", None)
        active = message.get("active", False)
        settings_data = {}
        settings_data["current_tool"] = tool.value if active else None
        print(settings_data, tool, active)
        self.update_application_settings(**settings_data)
        # self.api.art.canvas.tool_changed(tool, active)
        self._update_action_buttons(tool, active)
        self._update_cursor()

    def save_state(self):
        save_splitter_settings(self.ui, ["splitter"])

    def on_toggle_grid_signal(self, message: Dict):
        val = message.get("show_grid", True)
        self.ui.grid_button.blockSignals(True)
        self.ui.grid_button.setChecked(val)
        self.ui.grid_button.blockSignals(False)
        self.update_grid_settings(show_grid=val)

    def on_toggle_grid_snap_signal(self, message: Dict):
        val = message.get("snap_to_grid", True)
        self.ui.snap_to_grid_button.blockSignals(True)
        self.ui.snap_to_grid_button.setChecked(val)
        self.ui.snap_to_grid_button.blockSignals(False)
        self.update_grid_settings(snap_to_grid=val)

    def color_button_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.brush_settings.primary_color = color.name()
            self.update_brush_settings(primary_color=color.name())
            self.set_button_color()
            self.api.art.canvas.brush_color_changed(color.name())

    def set_button_color(self):
        color = self.brush_settings.primary_color
        self.ui.brush_color_button.setStyleSheet(f"background-color: {color};")

    def _update_action_buttons(self, tool, active):
        self.ui.active_grid_area_button.blockSignals(True)
        self.ui.brush_button.blockSignals(True)
        self.ui.eraser_button.blockSignals(True)
        self.ui.text_button.blockSignals(True)
        self.ui.grid_button.blockSignals(True)
        self.ui.move_button.blockSignals(True)
        self.ui.active_grid_area_button.setChecked(
            tool is CanvasToolName.ACTIVE_GRID_AREA and active
        )
        self.ui.move_button.setChecked(tool is CanvasToolName.MOVE and active)
        self.ui.brush_button.setChecked(
            tool is CanvasToolName.BRUSH and active
        )
        self.ui.eraser_button.setChecked(
            tool is CanvasToolName.ERASER and active
        )
        self.ui.text_button.setChecked(tool is CanvasToolName.TEXT and active)
        self.ui.grid_button.setChecked(self.grid_settings.show_grid)
        self.ui.active_grid_area_button.blockSignals(False)
        self.ui.brush_button.blockSignals(False)
        self.ui.eraser_button.blockSignals(False)
        self.ui.text_button.blockSignals(False)
        self.ui.grid_button.blockSignals(False)
        self.ui.move_button.blockSignals(False)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._default_splitter_settings_applied and self.isVisible():
            self._apply_default_splitter_settings()
            self._default_splitter_settings_applied = True

        self.set_prompt_editor_button_checked()
        self.set_art_tools_button_checked()

        if not self._initialized:
            self._initialized = True
            self._update_cursor()

    def on_canvas_update_cursor_signal(self, message: Dict):
        self._update_cursor(message)

    def _apply_default_splitter_settings(self):
        """
        Applies default splitter sizes. Called to ensure
        widget geometry is more likely to be initialized.
        """
        if hasattr(self, "ui") and self.ui is not None:
            QApplication.processEvents()  # Ensure pending layout events are processed
            default_canvas_splitter_config = {
                "splitter": {
                    "index_to_maximize": 1,
                    "min_other_size": 50,
                }
            }
            load_splitter_settings(
                self.ui,
                self._splitters,  # Uses self._splitters defined in __init__
                default_maximize_config=default_canvas_splitter_config,
            )
        else:
            # This case should ideally not happen if __init__ completed successfully.
            # Consider logging if a logger is available and configured for this class.
            self.logger.error(
                f"Error in CanvasWidget: UI not available when attempting to apply default splitter settings."
            )

    def _update_cursor(self, message: Optional[Dict] = None):
        message = message or {}
        event = message.get("event", None)
        current_tool = message.get("current_tool", self.current_tool)
        cursor = None

        if message.get("apply_cursor", False):
            # Handle different event types
            if (
                event
                and hasattr(event, "button")
                and event.button() == Qt.MouseButton.MiddleButton
            ):
                cursor = Qt.CursorShape.ClosedHandCursor
            elif current_tool in (
                CanvasToolName.BRUSH,
                CanvasToolName.ERASER,
            ):
                cursor = circle_cursor(
                    Qt.GlobalColor.white,
                    Qt.GlobalColor.transparent,
                    self.brush_settings.size,
                )
            elif current_tool in (
                CanvasToolName.ACTIVE_GRID_AREA,
                CanvasToolName.MOVE,
            ):
                # For enterEvent (event is None) or events without left button pressed
                if (
                    event
                    and hasattr(event, "buttons")
                    and event.buttons() == Qt.MouseButton.LeftButton
                ):
                    cursor = Qt.CursorShape.ClosedHandCursor
                else:
                    cursor = Qt.CursorShape.OpenHandCursor
            elif current_tool is CanvasToolName.NONE:
                cursor = Qt.CursorShape.ArrowCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor

        # Only set cursor if it changed
        if (
            not hasattr(self, "_current_cursor")
            or self._current_cursor != cursor
        ):
            if cursor is not None:
                self.setCursor(cursor)
            self._current_cursor = cursor

    def toggle_grid(self, _val):
        self.do_draw()

    def do_draw(self, force_draw: bool = False):
        self.api.art.canvas.do_draw(force_draw)
        self.ui.canvas_container_size = (
            self.ui.canvas_container.viewport().size()
        )

    def _clear_canvas_state(self) -> None:
        """Clear the scene and reset widget-level caches."""

        self.api.art.canvas.clear()
        self.images.clear()
        self.current_image_index = 0
        self.draggable_pixmaps_in_scene.clear()
        self.active_grid_area_pivot_point = QPoint(0, 0)
        self.active_grid_area_position = QPoint(0, 0)

    def _delete_all_layers(self) -> bool:
        """Delete every canvas layer and its associated records."""

        layers = CanvasLayer.objects.order_by("order").all() or []
        layer_ids = [layer.id for layer in layers]

        if not layer_ids:
            return True

        self.api.art.canvas.begin_layer_operation("delete", layer_ids)
        try:
            for layer_id in layer_ids:
                self.api.art.canvas.layer_deleted(layer_id)
                self._delete_layer_records(layer_id)
            self.api.art.canvas.commit_layer_operation("delete", layer_ids)
        except Exception as exc:  # pragma: no cover - protective guard
            self.api.art.canvas.cancel_layer_operation("delete")
            if hasattr(self, "logger"):
                self.logger.exception(exc)

    def _serialize_canvas_document(self) -> Dict[str, Any]:
        """Create a serializable snapshot of all layers on the canvas."""

        layers = CanvasLayer.objects.order_by("order").all() or []
        document_layers: List[Dict[str, Any]] = []

        indexed_layers = list(enumerate(layers))
        ordered_layers = sorted(
            indexed_layers,
            key=lambda pair: (
                getattr(pair[1], "order", pair[0]) or pair[0],
                pair[0],
            ),
        )

        for fallback_index, layer in ordered_layers:
            document_layers.append(
                {
                    "name": layer.name,
                    "order": (
                        layer.order
                        if layer.order is not None
                        else fallback_index
                    ),
                    "visible": bool(layer.visible),
                    "locked": bool(layer.locked),
                    "opacity": (
                        layer.opacity if layer.opacity is not None else 0
                    ),
                    "blend_mode": layer.blend_mode or "normal",
                    "drawing_pad": self._serialize_drawing_pad_settings(
                        layer.id
                    ),
                }
            )

        return {
            "version": 1,
            "layers": document_layers,
        }

    def _serialize_drawing_pad_settings(self, layer_id: int) -> Dict[str, Any]:
        """Serialize drawing pad settings for persistence."""

        settings = DrawingPadSettings.objects.filter_by_first(
            layer_id=layer_id
        )
        if not settings:
            return {}

        return {
            "x_pos": settings.x_pos or 0,
            "y_pos": settings.y_pos or 0,
            "image": self._encode_binary(settings.image),
            "mask": self._encode_binary(settings.mask),
        }

    def _clear_canvas(self):
        self._clear_canvas_state()
        self._delete_all_layers()
        DrawingPadSettings.objects.delete_all()
        ControlnetSettings.objects.delete_all()
        ImageToImageSettings.objects.delete_all()
        OutpaintSettings.objects.delete_all()
        self.api.art.canvas.clear_history()

    def _reset_canvas_document(self) -> None:
        self._clear_canvas()

        self.api.art.canvas.begin_layer_operation("create")
        new_layer = None
        try:
            new_layer = self._create_default_canvas_layer()
            if new_layer is None:
                raise RuntimeError("Failed to create default canvas layer")
            self.api.art.canvas.commit_layer_operation(
                "create", [new_layer.id]
            )
        except Exception as exc:  # pragma: no cover - protective guard
            self.api.art.canvas.cancel_layer_operation("create")
            if hasattr(self, "logger"):
                self.logger.exception(exc)
            return

        self.api.art.canvas.show_layers()

        if new_layer is not None:
            self.api.art.canvas.layer_selection_changed([new_layer.id])

        self.api.art.canvas.update_image_positions()

    def _load_canvas_document(self, document: Dict[str, Any]) -> None:
        """Restore layers from a serialized document."""

        if not isinstance(document, dict):
            raise ValueError("Invalid document format.")

        version = document.get("version", 1)
        if version != 1:
            raise ValueError(f"Unsupported document version: {version}")

        layers_data = document.get("layers", []) or []

        self._clear_canvas()

        created_layer_ids: List[int] = []

        if layers_data:
            self.api.art.canvas.begin_layer_operation("create")
            try:
                indexed_layers = list(enumerate(layers_data))
                ordered_layers = sorted(
                    indexed_layers,
                    key=lambda item: item[1].get("order", item[0]),
                )
                for fallback_index, snapshot in ordered_layers:
                    layer = self._create_layer_from_snapshot(
                        snapshot, fallback_index
                    )
                    if layer is None:
                        raise RuntimeError(
                            "Failed to create layer from document"
                        )
                    created_layer_ids.append(layer.id)
                self.api.art.canvas.commit_layer_operation(
                    "create", created_layer_ids
                )
            except Exception:
                self.api.art.canvas.cancel_layer_operation("create")
                raise
        else:
            self.api.art.canvas.begin_layer_operation("create")
            try:
                default_layer = self._create_default_canvas_layer()
                if default_layer is None:
                    raise RuntimeError("Failed to create default canvas layer")
                created_layer_ids.append(default_layer.id)
                self.api.art.canvas.commit_layer_operation(
                    "create", created_layer_ids
                )
            except Exception:
                self.api.art.canvas.cancel_layer_operation("create")
                raise

        self.api.art.canvas.show_layers()

        if created_layer_ids:
            self.api.art.canvas.layer_selection_changed([created_layer_ids[0]])

        self.api.art.canvas.update_image_positions()

    def _create_layer_from_snapshot(
        self, snapshot: Dict[str, Any], fallback_order: int
    ) -> Optional[CanvasLayer]:
        """Create a new layer using serialized snapshot data."""

        layer_kwargs = {
            "order": snapshot.get("order", fallback_order),
            "name": snapshot.get("name") or f"Layer {fallback_order + 1}",
            "visible": snapshot.get("visible", True),
            "locked": snapshot.get("locked", False),
            "opacity": snapshot.get("opacity", 100),
            "blend_mode": snapshot.get("blend_mode", "normal"),
        }

        layer = CanvasLayer.objects.create(**layer_kwargs)
        if layer is None:
            return None

        self._initialize_layer_defaults(layer.id)

        drawing_snapshot = snapshot.get("drawing_pad") or {}
        updates: Dict[str, Any] = {}

        if "x_pos" in drawing_snapshot:
            x_pos = drawing_snapshot.get("x_pos")
            updates["x_pos"] = int(x_pos) if x_pos is not None else 0
        if "y_pos" in drawing_snapshot:
            y_pos = drawing_snapshot.get("y_pos")
            updates["y_pos"] = int(y_pos) if y_pos is not None else 0

        image_data = drawing_snapshot.get("image")
        mask_data = drawing_snapshot.get("mask")

        decoded_image = self._decode_binary(image_data)
        decoded_mask = self._decode_binary(mask_data)

        if decoded_image is not None:
            updates["image"] = decoded_image
        if decoded_mask is not None:
            updates["mask"] = decoded_mask

        if updates:
            self.update_drawing_pad_settings(layer_id=layer.id, **updates)

        return layer

    @staticmethod
    def _encode_binary(data: Optional[bytes]) -> Optional[str]:
        """Encode binary data as a base64 string for storage."""

        if not data:
            return None
        return base64.b64encode(data).decode("utf-8")

    @staticmethod
    def _decode_binary(value: Optional[str]) -> Optional[bytes]:
        """Decode a base64 string into binary data."""

        if not value:
            return None
        try:
            return base64.b64decode(value)
        except Exception:
            return None

    def _show_error_message(self, title: str, message: str) -> None:
        """Display an error message to the user."""

        try:
            QMessageBox.critical(self, title, message)
        except Exception:  # pragma: no cover - best effort logging fallback
            if hasattr(self, "logger"):
                self.logger.error(f"{title}: {message}")

    def _delete_layer_records(self, layer_id: int) -> None:
        CanvasLayer.objects.delete(layer_id)
        DrawingPadSettings.objects.delete_by(layer_id=layer_id)
        ControlnetSettings.objects.delete_by(layer_id=layer_id)
        ImageToImageSettings.objects.delete_by(layer_id=layer_id)
        OutpaintSettings.objects.delete_by(layer_id=layer_id)

    def _create_default_canvas_layer(self) -> Optional[CanvasLayer]:
        layer = CanvasLayer.objects.create(
            order=0,
            name="Layer 1",
            visible=True,
            opacity=100,
        )

        if layer is None:
            return None

        self._initialize_layer_defaults(layer.id)
        return layer

    @staticmethod
    def _initialize_layer_defaults(layer_id: int) -> None:
        try:
            if not DrawingPadSettings.objects.filter_by(layer_id=layer_id):
                DrawingPadSettings.objects.create(layer_id=layer_id)

            if not ControlnetSettings.objects.filter_by(layer_id=layer_id):
                ControlnetSettings.objects.create(layer_id=layer_id)

            if not ImageToImageSettings.objects.filter_by(layer_id=layer_id):
                ImageToImageSettings.objects.create(layer_id=layer_id)

            if not OutpaintSettings.objects.filter_by(layer_id=layer_id):
                OutpaintSettings.objects.create(layer_id=layer_id)

            if not BrushSettings.objects.filter_by(layer_id=layer_id):
                BrushSettings.objects.create(layer_id=layer_id)

            if not MetadataSettings.objects.filter_by(layer_id=layer_id):
                MetadataSettings.objects.create(layer_id=layer_id)
        except Exception:  # pragma: no cover - defensive fallback
            # Logging occurs at manager level; no additional handling required
            pass
