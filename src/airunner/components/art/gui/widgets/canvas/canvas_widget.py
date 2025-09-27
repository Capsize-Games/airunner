from PySide6.QtWidgets import QColorDialog
from PySide6.QtWidgets import QFileDialog
from typing import Optional, Dict

from PySide6.QtCore import Qt, QPoint
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication

from airunner.gui.cursors.circle_brush import circle_cursor
from airunner.enums import SignalCode, CanvasToolName
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.canvas.templates.canvas_ui import (
    Ui_canvas,
)
from airunner.utils.application import set_widget_state
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
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
        }
        self._initialized: bool = False
        self._splitters = ["canvas_splitter"]
        self._default_splitter_settings_applied = False
        super().__init__(*args, **kwargs)

        # Configure default splitter sizes for canvas_splitter
        # Assuming the main canvas area is the second panel (index 1)
        default_canvas_splitter_config = {
            "canvas_splitter": {"index_to_maximize": 1, "min_other_size": 50}
        }
        load_splitter_settings(
            self.ui,
            self._splitters,  # self._splitters is ["canvas_splitter"]
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
        self.ui.grid_button.setChecked(show_grid)
        self.ui.grid_button.blockSignals(False)

        set_widget_state(
            self.ui.grid_button,
            current_tool is CanvasToolName.ACTIVE_GRID_AREA,
        )
        set_widget_state(
            self.ui.brush_button, current_tool is CanvasToolName.BRUSH
        )
        set_widget_state(
            self.ui.eraser_button, current_tool is CanvasToolName.ERASER
        )
        set_widget_state(
            self.ui.text_button, current_tool is CanvasToolName.TEXT
        )
        set_widget_state(self.ui.grid_button, show_grid is True)

        self.set_button_color()

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
    def on_new_button_clicked(self):
        self._reset_canvas_document()

    @Slot()
    def on_open_art_document_clicked(self):
        print("on_open_art_document")

    @Slot()
    def on_save_art_document_clicked(self):
        print("on_save_art_document")

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

    def on_toggle_grid_signal(self, message: Dict):
        self.ui.grid_button.setChecked(message.get("show_grid", True))

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
        self.ui.active_grid_area_button.setChecked(
            tool is CanvasToolName.ACTIVE_GRID_AREA and active
        )
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

    def showEvent(self, event):
        super().showEvent(event)
        if not self._default_splitter_settings_applied and self.isVisible():
            self._apply_default_splitter_settings()
            self._default_splitter_settings_applied = True

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
                "canvas_splitter": {
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
            print(
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
            elif current_tool is CanvasToolName.ACTIVE_GRID_AREA:
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

    def _reset_canvas_document(self) -> None:
        self.api.art.canvas.clear()
        self.images.clear()
        self.current_image_index = 0
        self.draggable_pixmaps_in_scene.clear()
        self.active_grid_area_pivot_point = QPoint(0, 0)
        self.active_grid_area_position = QPoint(0, 0)

        layers = CanvasLayer.objects.order_by("order").all() or []
        layer_ids = [layer.id for layer in layers]

        if layer_ids:
            self.api.art.canvas.begin_layer_operation("delete", layer_ids)
            try:
                for layer_id in layer_ids:
                    self.emit_signal(
                        SignalCode.LAYER_DELETED,
                        {"layer_id": layer_id},
                    )
                    self._delete_layer_records(layer_id)
                self.api.art.canvas.commit_layer_operation("delete", layer_ids)
            except Exception as exc:  # pragma: no cover - protective guard
                self.api.art.canvas.cancel_layer_operation("delete")
                if hasattr(self, "logger"):
                    self.logger.exception(exc)
                return

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
            self.emit_signal(
                SignalCode.LAYER_SELECTION_CHANGED,
                {"selected_layer_ids": [new_layer.id]},
            )

    def _delete_layer_records(self, layer_id: int) -> None:
        CanvasLayer.objects.delete(layer_id)
        DrawingPadSettings.objects.delete_by(layer_id=layer_id)
        ControlnetSettings.objects.delete_by(layer_id=layer_id)
        ImageToImageSettings.objects.delete_by(layer_id=layer_id)
        OutpaintSettings.objects.delete_by(layer_id=layer_id)
        BrushSettings.objects.delete_by(layer_id=layer_id)
        MetadataSettings.objects.delete_by(layer_id=layer_id)

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
