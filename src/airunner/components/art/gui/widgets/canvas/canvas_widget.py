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
from airunner.components.data.session_manager import _get_session
from airunner.components.art.gui.widgets.canvas.templates.canvas_ui import (
    Ui_canvas,
)
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
from airunner.components.art.gui.windows.filter_list_window.filter_list_window import (
    FilterListWindow,
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
        ("folder", "open_art_document"),
        ("save", "save_art_document"),
        ("link-2", "snap_to_grid_button"),
        ("move", "move_button"),
        ("message-square", "prompt_editor_button"),
        ("tool", "art_tools_button"),
        ("filter", "filter_button"),
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
        self.load_splitter_settings(
            default_maximize_config=default_canvas_splitter_config
        )

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
        # Ensure toolbar buttons use pointing hand cursor where applicable
        try:
            for btn_name in (
                "upscale_x4",
                "new_button",
                "import_button",
                "export_button",
                "recenter_button",
                "active_grid_area_button",
                "brush_button",
                "eraser_button",
                "grid_button",
                "undo_button",
                "redo_button",
            ):
                btn = getattr(self.ui, btn_name, None)
                if btn is not None:
                    btn.setCursor(Qt.PointingHandCursor)
        except Exception:
            pass

    _offset_x = 0
    _offset_y = 0

    @property
    def offset_x(self) -> int:
        """Get the current X offset of the canvas.

        Returns:
            The X offset in pixels.
        """
        return self._offset_x

    @offset_x.setter
    def offset_x(self, value: int) -> None:
        """Set the X offset of the canvas.

        Args:
            value: The X offset in pixels.
        """
        self._offset_x = value

    @property
    def offset_y(self) -> int:
        """Get the current Y offset of the canvas.

        Returns:
            The Y offset in pixels.
        """
        return self._offset_y

    @offset_y.setter
    def offset_y(self, value: int) -> None:
        """Set the Y offset of the canvas.

        Args:
            value: The Y offset in pixels.
        """
        self._offset_y = value

    def update_grid_info(self, data: Dict) -> None:
        """Update the grid info display with position and zoom level.

        Args:
            data: Dictionary containing offset_x, offset_y, and optionally zoom level.
        """
        self.offset_x = data.get("offset_x", self.offset_x)
        self.offset_y = data.get("offset_y", self.offset_y)
        zoom_level = round(self.grid_settings.zoom_level * 100, 2)
        self.ui.grid_info.setText(
            f"{self.offset_x}, {self.offset_y}, {zoom_level}%"
        )

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
    def image_pivot_point(self) -> QPoint:
        """Get the current image pivot point.

        Returns:
            QPoint representing the pivot point coordinates.
        """
        settings = self.application_settings
        try:
            return QPoint(settings.pivot_point_x, settings.pivot_point_y)
        except Exception as e:
            self.logger.error(e)
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value: QPoint) -> None:
        """Set the image pivot point.

        Args:
            value: QPoint representing the new pivot point coordinates.
        """
        settings = self.application_settings
        settings.pivot_point_x = value.x()
        settings.pivot_point_y = value.y()
        self.update_application_settings(pivot_point_x=value.x())
        self.update_application_settings(pivot_point_y=value.y())

    @Slot(bool)
    def on_prompt_editor_button_clicked(self, val: bool) -> None:
        """Handle prompt editor button toggle.

        Args:
            val: True if button is checked, False otherwise.
        """
        self._toggle_splitter_section(val, 0, self.ui.splitter)

    @Slot(bool)
    def on_art_tools_button_clicked(self, val: bool) -> None:
        """Handle art tools button toggle.

        Args:
            val: True if button is checked, False otherwise.
        """
        self._toggle_splitter_section(val, 2, self.ui.splitter, 300)

    def on_splitter_changed_sizes(self) -> None:
        """Handle splitter size changes by updating button states."""
        self.set_prompt_editor_button_checked()
        self.set_art_tools_button_checked()

    def set_prompt_editor_button_checked(self) -> None:
        """Update prompt editor button checked state based on splitter size."""
        self.ui.prompt_editor_button.blockSignals(True)
        self.ui.prompt_editor_button.setChecked(
            self.ui.splitter.sizes()[0] > 0
        )
        self.ui.prompt_editor_button.blockSignals(False)

    def set_art_tools_button_checked(self) -> None:
        """Update art tools button checked state based on splitter size."""
        self.ui.art_tools_button.blockSignals(True)
        self.ui.art_tools_button.setChecked(self.ui.splitter.sizes()[2] > 0)
        self.ui.art_tools_button.blockSignals(False)

    @Slot()
    def on_brush_color_button_clicked(self) -> None:
        """Handle brush color button click to open color picker."""
        self.color_button_clicked()

    @Slot()
    def on_recenter_button_clicked(self) -> None:
        """Handle recenter button click to recenter the grid."""
        self.api.art.canvas.recenter_grid()

    @Slot()
    def on_undo_button_clicked(self) -> None:
        """Handle undo button click to undo last action."""
        self.api.art.canvas.undo()

    @Slot()
    def on_redo_button_clicked(self) -> None:
        """Handle redo button click to redo last undone action."""
        self.api.art.canvas.redo()

    @Slot()
    def on_new_button_clicked(self) -> None:
        """Handle new button click to create a new canvas document."""
        self._reset_canvas_document()

    @Slot(bool)
    def on_grid_button_toggled(self, val: bool) -> None:
        """Handle grid button toggle to show/hide grid.

        Args:
            val: True if grid should be shown, False otherwise.
        """
        self.api.art.canvas.toggle_grid(val)

    @Slot(bool)
    def on_snap_to_grid_button_toggled(self, val: bool) -> None:
        """Handle snap to grid button toggle.

        Args:
            val: True if snap to grid should be enabled, False otherwise.
        """
        self.api.art.canvas.toggle_grid_snap(val)

    @Slot()
    def on_import_button_clicked(self) -> None:
        """Handle import button click to import an image."""
        self.api.art.canvas.import_image()

    @Slot()
    def on_export_button_clicked(self) -> None:
        """Handle export button click to export the canvas."""
        self.api.art.canvas.export_image()

    @Slot()
    def on_open_art_document_clicked(self) -> None:
        """Handle open art document button click to load a saved document."""
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
            self.logger.exception(exc)
            return

        try:
            self._load_canvas_document(document)
        except Exception as exc:  # pragma: no cover - defensive UI feedback
            self._show_error_message(
                "Open Document Failed",
                "The document could not be loaded.",
            )
            self.logger.error(exc)

    @Slot()
    def on_save_art_document_clicked(self) -> None:
        """Handle save art document button click to save the current document."""
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
            self.logger.exception(exc)

    @Slot()
    def on_filter_button_clicked(self) -> None:
        """Handle filter button click to open the filter list window."""
        try:
            # Keep the dialog attached to the widget so it is not garbage
            # collected immediately by Python.
            if getattr(self, "_filter_list_window", None) is None:
                self._filter_list_window = FilterListWindow(parent=self)
                try:
                    # Clear the cached ref when the dialog is closed so it
                    # can be recreated the next time the button is clicked.
                    self._filter_list_window.finished.connect(
                        lambda _code: setattr(
                            self, "_filter_list_window", None
                        )
                    )
                except Exception:
                    pass
            else:
                try:
                    self._filter_list_window.raise_()
                except Exception:
                    pass
        except Exception as exc:
            self.logger.exception("Failed to open FilterListWindow: %s", exc)

    @Slot(bool)
    def on_brush_button_toggled(self, val: bool) -> None:
        """Handle brush tool button toggle.

        Args:
            val: True if brush tool should be activated, False otherwise.
        """
        self.api.art.canvas.toggle_tool(CanvasToolName.BRUSH, val)

    @Slot(bool)
    def on_eraser_button_toggled(self, val: bool) -> None:
        """Handle eraser tool button toggle.

        Args:
            val: True if eraser tool should be activated, False otherwise.
        """
        self.api.art.canvas.toggle_tool(CanvasToolName.ERASER, val)
        self._update_cursor()

    @Slot(bool)
    def on_active_grid_area_button_toggled(self, val: bool) -> None:
        """Handle active grid area tool button toggle.

        Args:
            val: True if active grid area tool should be activated, False otherwise.
        """
        self.api.art.canvas.toggle_tool(CanvasToolName.ACTIVE_GRID_AREA, val)

    @Slot(bool)
    def on_move_button_toggled(self, val: bool) -> None:
        """Handle move tool button toggle.

        Args:
            val: True if move tool should be activated, False otherwise.
        """
        self.api.art.canvas.toggle_tool(CanvasToolName.MOVE, val)

    def on_toggle_tool_signal(self, message: Dict) -> None:
        """Handle tool toggle signal from other components.

        Args:
            message: Dictionary containing tool and active state information.
        """
        if (
            hasattr(self, "_processing_tool_change")
            and self._processing_tool_change
        ):
            return

        self._processing_tool_change = True
        try:
            tool = message.get("tool", None)
            active = message.get("active", False)
            settings_data = {"current_tool": tool.value if active else None}
            self.update_application_settings(**settings_data)
            self.api.art.canvas.tool_changed(tool, active)
            self._update_action_buttons(tool, active)
            self._update_cursor()
        finally:
            self._processing_tool_change = False

    def save_state(self) -> None:
        """Save the current widget state including splitter positions."""
        self._save_splitter_state()

    def on_toggle_grid_signal(self, message: Dict) -> None:
        """Handle grid toggle signal to show/hide the grid.

        Args:
            message: Dictionary containing show_grid boolean.
        """
        val = message.get("show_grid", True)
        self.ui.grid_button.blockSignals(True)
        self.ui.grid_button.setChecked(val)
        self.ui.grid_button.blockSignals(False)
        self.update_grid_settings(show_grid=val)

    def on_toggle_grid_snap_signal(self, message: Dict) -> None:
        """Handle grid snap toggle signal.

        Args:
            message: Dictionary containing snap_to_grid boolean.
        """
        val = message.get("snap_to_grid", True)
        self.ui.snap_to_grid_button.blockSignals(True)
        self.ui.snap_to_grid_button.setChecked(val)
        self.ui.snap_to_grid_button.blockSignals(False)
        self.update_grid_settings(snap_to_grid=val)

    def color_button_clicked(self) -> None:
        """Open color picker dialog and update brush color."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.brush_settings.primary_color = color.name()
            self.update_brush_settings(primary_color=color.name())
            self.set_button_color()
            self.api.art.canvas.brush_color_changed(color.name())

    def set_button_color(self) -> None:
        """Update the brush color button's background color."""
        color = self.brush_settings.primary_color
        self.ui.brush_color_button.setStyleSheet(f"background-color: {color};")

    def _update_action_buttons(self, tool, active):
        self.ui.active_grid_area_button.blockSignals(True)
        self.ui.brush_button.blockSignals(True)
        self.ui.eraser_button.blockSignals(True)
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
        self.ui.grid_button.setChecked(self.grid_settings.show_grid)
        self.ui.active_grid_area_button.blockSignals(False)
        self.ui.brush_button.blockSignals(False)
        self.ui.eraser_button.blockSignals(False)
        self.ui.grid_button.blockSignals(False)
        self.ui.move_button.blockSignals(False)

    def showEvent(self, event: Any) -> None:
        """Handle widget show event to initialize splitter and cursor.

        Args:
            event: The show event.
        """
        super().showEvent(event)
        if not self._default_splitter_settings_applied and self.isVisible():
            self._apply_default_splitter_settings()
            self._default_splitter_settings_applied = True

        self.set_prompt_editor_button_checked()
        self.set_art_tools_button_checked()

        if not self._initialized:
            self._initialized = True
            self._update_cursor()

    def on_canvas_update_cursor_signal(self, message: Dict) -> None:
        """Handle cursor update signal.

        Args:
            message: Dictionary containing cursor update information.
        """
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
            self.load_splitter_settings(
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

    def toggle_grid(self, _val: bool) -> None:
        """Toggle grid visibility and redraw canvas.

        Args:
            _val: Grid visibility state (unused, triggers redraw).
        """
        self.do_draw()

    def do_draw(self, force_draw: bool = False) -> None:
        """Request canvas redraw.

        Args:
            force_draw: If True, force redraw even if already drawing.
        """
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
        # Start a grouped delete operation and perform direct DB deletes.
        # Relying on the UI signal handler to perform DB deletes can fail
        # if the UI isn't listening; delete directly to ensure a clean
        # state when creating a new document.
        self.api.art.canvas.begin_layer_operation("delete", layer_ids)
        try:
            for layer_id in layer_ids:
                self._delete_layer_records(layer_id)

            self.api.art.canvas.commit_layer_operation("delete", layer_ids)

            # Notify other components to refresh their layer displays
            # after the DB-level deletion.
            self.api.art.canvas.show_layers()
            return True
        except Exception as exc:  # pragma: no cover - protective guard
            self.api.art.canvas.cancel_layer_operation("delete")
            self.logger.exception(exc)
            return False

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

        # Ensure any previous scoped session state is cleared (e.g. after a
        # rolled-back transaction). This prevents "Session's transaction has
        # been rolled back" errors when creating new rows with UNIQUE
        # constraints (e.g. layer names).
        try:
            _get_session().remove()
        except Exception:
            # Non-fatal; continue to begin operation regardless
            pass

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
            self.logger.error(exc)
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
            try:
                _get_session().remove()
            except Exception:
                pass
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
            try:
                _get_session().remove()
            except Exception:
                pass
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
            self.logger.error(f"{title}: {message}")

    def _delete_layer_records(self, layer_id: int) -> None:
        DrawingPadSettings.objects.delete_by(layer_id=layer_id)
        ControlnetSettings.objects.delete_by(layer_id=layer_id)
        ImageToImageSettings.objects.delete_by(layer_id=layer_id)
        OutpaintSettings.objects.delete_by(layer_id=layer_id)
        CanvasLayer.objects.delete(layer_id)

    def _create_default_canvas_layer(self) -> Optional[CanvasLayer]:
        # Ensure any previous scoped session state is cleared
        try:
            _get_session().remove()
        except Exception:
            pass

        # Pick a non-conflicting default name (Layer 1, Layer 2, ...)
        base = "Layer"
        index = 1
        name = f"{base} {index}"
        # Loop until we find an unused name
        while CanvasLayer.objects.filter_by(name=name):
            index += 1
            name = f"{base} {index}"

        layer = CanvasLayer.objects.create(
            order=0,
            name=name,
            visible=True,
            opacity=100,
        )

        if layer is None:
            return None

        self._initialize_layer_defaults(layer.id)
        return layer

    @staticmethod
    def _initialize_layer_defaults(layer_id: int) -> None:
        """Initialize default settings for a new layer.

        Args:
            layer_id: The ID of the layer to initialize settings for.
        """
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
