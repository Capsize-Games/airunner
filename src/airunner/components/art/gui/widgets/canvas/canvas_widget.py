import base64
import json
from pathlib import Path

from PySide6.QtWidgets import QColorDialog
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QMessageBox
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtCore import Slot
from PySide6.QtGui import QKeySequence, QShortcut

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
        ("pencil", "brush_button"),
        ("eraser", "eraser_button"),
        ("grid-3x3", "grid_button"),
        ("undo", "undo_button"),
        ("redo", "redo_button"),
        ("folder", "open_art_document"),
        ("save", "save_art_document"),
        ("link-2", "snap_to_grid_button"),
        ("move", "move_button"),
        ("filter", "filter_button"),
        ("image-minus", "remove_background_button"),
    ]

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.ENABLE_BRUSH_TOOL_SIGNAL: lambda _message: self.on_brush_button_toggled(
                True
            ),
            SignalCode.ENABLE_ERASER_TOOL_SIGNAL: lambda _message: self.on_eraser_button_toggled(
                True
            ),
            SignalCode.ENABLE_MOVE_TOOL_SIGNAL: lambda _message: self.on_move_button_toggled(
                True
            ),
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_toggle_tool_signal,
            SignalCode.TOGGLE_TOOL: self.on_toggle_tool_signal,
            SignalCode.TOGGLE_GRID: self.on_toggle_grid_signal,
            SignalCode.TOGGLE_GRID_SNAP: self.on_toggle_grid_snap_signal,
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
            SignalCode.CANVAS_UPDATE_GRID_INFO: self.update_grid_info,
            SignalCode.CANVAS_ZOOM_LEVEL_CHANGED: self.update_grid_info,
            SignalCode.LAYER_SELECTION_CHANGED: (
                self.on_layer_selection_changed_signal
            ),
            SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED: (
                self.on_active_grid_area_updated_signal
            ),
            SignalCode.SAVE_STATE: self.save_state,
        }
        self._initialized: bool = False
        self._splitters = []
        self._centered_canvas_restore_scheduled = False
        super().__init__(*args, **kwargs)
        self._configure_canvas_shortcuts()

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
        self._update_status_labels()

    @staticmethod
    def _to_bool(value: Any) -> bool:
        """Coerce persisted settings values into booleans."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        return bool(value)

    def _should_restore_centered_canvas(self) -> bool:
        """Return whether startup should restore the centered viewport."""
        centered_state = self.settings.value("canvas_is_centered", None)
        if centered_state is not None:
            return self._to_bool(centered_state)

        raw_x = self.settings.value("canvas_offset_x", 0.0)
        raw_y = self.settings.value("canvas_offset_y", 0.0)
        try:
            offset_x = float(raw_x) if raw_x is not None else 0.0
            offset_y = float(raw_y) if raw_y is not None else 0.0
        except (TypeError, ValueError):
            return False

        return abs(offset_x) < 1e-6 and abs(offset_y) < 1e-6

    def _update_status_labels(self) -> None:
        """Refresh the bottom status labels for view and active item."""
        zoom_level = round(self.grid_settings.zoom_level * 100, 2)
        grid_info = getattr(self.ui, "grid_info", None)
        if grid_info is not None:
            grid_info.setText(
                f"{self.offset_x}, {self.offset_y}, {zoom_level}%"
            )

        active_item_info = getattr(self.ui, "active_item_info", None)
        if active_item_info is not None:
            active_item_info.setText(self._get_active_item_status_text())

    def _get_active_item_status_text(self) -> str:
        """Return the status text for the active movable canvas item."""
        tool = self.current_tool
        if tool is CanvasToolName.ACTIVE_GRID_AREA:
            return self._format_active_position(
                "Grid",
                self.active_grid_settings.pos_x,
                self.active_grid_settings.pos_y,
            )
        if tool is CanvasToolName.MOVE:
            return self._format_active_position(
                "Layer",
                self.drawing_pad_settings.x_pos,
                self.drawing_pad_settings.y_pos,
            )
        return ""

    @staticmethod
    def _format_active_position(
        label: str,
        pos_x: Any,
        pos_y: Any,
    ) -> str:
        """Return a compact active-item coordinate string."""
        x_pos = int(pos_x) if pos_x is not None else 0
        y_pos = int(pos_y) if pos_y is not None else 0
        return f"{label}: {x_pos}, {y_pos}"

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

    @Slot()
    def on_brush_color_button_clicked(self) -> None:
        """Handle brush color button click to open color picker."""
        self.color_button_clicked()

    @Slot()
    def on_remove_background_button_clicked(self) -> None:
        """Handle remove background button click."""
        self.api.art.canvas.remove_background()

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
            self._update_cursor(
                {
                    "apply_cursor": active,
                    "current_tool": tool,
                }
            )
            self._update_status_labels()
        finally:
            self._processing_tool_change = False

    def on_layer_selection_changed_signal(self, message: Dict) -> None:
        """Track layer selection updates and refresh the footer status."""
        self._on_layer_selection_changed(message)
        self._update_status_labels()

    def on_active_grid_area_updated_signal(
        self,
        _message: Optional[Dict] = None,
    ) -> None:
        """Refresh active-item coordinates after grid-position changes."""
        self._update_status_labels()

    def save_state(self) -> None:
        """Save the current widget state."""
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
        """Handle widget show event to initialize layout and cursor.

        Args:
            event: The show event.
        """
        super().showEvent(event)
        self._schedule_centered_canvas_restore()
        self._update_status_labels()

        if not self._initialized:
            self._initialized = True
            self._update_cursor({"apply_cursor": True})

    def refresh_layout_after_host_resize(self) -> None:
        """Recenter the canvas after the main splitter changes size."""
        self._schedule_centered_canvas_restore()

    def _configure_canvas_shortcuts(self) -> None:
        """Register keyboard shortcuts that only apply inside the canvas."""
        target = getattr(getattr(self, "ui", None), "canvas_container", None)
        self._canvas_shortcuts = []
        if target is None:
            return

        shortcuts = (
            ("Ctrl+Z", self.on_undo_button_clicked),
            ("Ctrl+Y", self.on_redo_button_clicked),
            ("Ctrl+Shift+Z", self.on_redo_button_clicked),
        )
        for sequence, handler in shortcuts:
            shortcut = self._create_canvas_shortcut(
                target,
                sequence,
                handler,
            )
            if shortcut is not None:
                self._canvas_shortcuts.append(shortcut)

    def _create_canvas_shortcut(
        self,
        target: Any,
        sequence: str,
        handler: Any,
    ) -> Optional[QShortcut]:
        """Create one canvas-local keyboard shortcut."""
        try:
            shortcut = QShortcut(QKeySequence(sequence), target)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            try:
                shortcut.setAutoRepeat(False)
            except Exception:
                pass
            shortcut.activated.connect(handler)
            return shortcut
        except Exception:
            self.logger.debug(
                "Could not create canvas shortcut %s",
                sequence,
            )
            return None

    def on_canvas_update_cursor_signal(self, message: Dict) -> None:
        """Handle cursor update signal.

        Args:
            message: Dictionary containing cursor update information.
        """
        self._update_cursor(message)

    def _schedule_centered_canvas_restore(self) -> None:
        """Defer centered-canvas sync until splitter layout changes settle."""
        view = getattr(getattr(self, "ui", None), "canvas_container", None)
        if view is None:
            return
        if not self._should_restore_centered_canvas():
            return
        if not (
            getattr(view, "_is_restoring_state", False)
            or getattr(view, "_needs_recenter_on_show", False)
        ):
            return
        if self._centered_canvas_restore_scheduled:
            return

        self._centered_canvas_restore_scheduled = True
        QTimer.singleShot(0, self._restore_centered_canvas_after_splitter)

    def _restore_centered_canvas_after_splitter(self) -> None:
        """Keep centered startup previews aligned with the final splitter size."""
        self._centered_canvas_restore_scheduled = False
        view = getattr(getattr(self, "ui", None), "canvas_container", None)
        if view is None:
            return
        if not self._should_restore_centered_canvas():
            return

        if getattr(view, "_is_restoring_state", False):
            if getattr(view, "_needs_recenter_on_show", False):
                view._preview_centered_layout()
                self.update_grid_info({})
            return

        if getattr(view, "_initialized", False):
            view.on_recenter_grid_signal()
            self.update_grid_info({})

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
