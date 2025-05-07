from typing import Optional, Dict

from PySide6.QtCore import Qt, QPoint
from PySide6.QtCore import Slot

from airunner.gui.cursors.circle_brush import circle_cursor
from airunner.enums import SignalCode, CanvasToolName
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.canvas.templates.canvas_ui import Ui_canvas
from airunner.utils.application import set_widget_state


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
        ("folder", "import_button"),
        ("save", "export_button"),
        ("target", "recenter_button"),
        ("object-selected-icon", "active_grid_area_button"),
        ("pencil-icon", "brush_button"),
        ("eraser-icon", "eraser_button"),
        ("grid", "grid_button"),
        ("corner-up-left", "undo_button"),
        ("corner-up-right", "redo_button"),
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
        super().__init__(*args, **kwargs)
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
        set_widget_state(self.ui.grid_button, show_grid is True)

    @property
    def current_tool(self):
        return CanvasToolName(self.application_settings.current_tool)

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
        self.update_application_settings("pivot_point_x", value.x())
        self.update_application_settings("pivot_point_y", value.y())

    @Slot()
    def on_recenter_button_clicked(self):
        self.api.art.canvas.recenter_grid()

    @Slot()
    def on_new_button_clicked(self):
        self.api.art.canvas.clear()

    @Slot()
    def on_import_button_clicked(self):
        self.api.art.canvas.import_image()

    @Slot()
    def on_export_button_clicked(self):
        self.api.art.canvas.export_image()

    @Slot()
    def on_undo_button_clicked(self):
        self.api.art.canvas.undo()

    @Slot()
    def on_redo_button_clicked(self):
        self.api.art.canvas.redo()

    @Slot(bool)
    def on_grid_button_toggled(self, val: bool):
        self.update_grid_settings("show_grid", val)

    @Slot(bool)
    def on_brush_button_toggled(self, val: bool):
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
        self._update_action_buttons(tool, active)
        self._update_cursor()

    def on_toggle_grid_signal(self, message: Dict):
        self.ui.grid_button.setChecked(message.get("show_grid", True))

    def _update_action_buttons(self, tool, active):
        self.ui.active_grid_area_button.setChecked(
            tool is CanvasToolName.ACTIVE_GRID_AREA and active
        )
        self.ui.brush_button.setChecked(
            tool is CanvasToolName.BRUSH and active
        )
        self.ui.eraser_button.setChecked(
            tool is CanvasToolName.ERASER and active
        )
        self.ui.grid_button.setChecked(self.grid_settings.show_grid)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initialized:
            self._initialized = True
            self._update_cursor()

    def on_canvas_update_cursor_signal(self, message: Dict):
        self._update_cursor(message)

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
        else:
            cursor = Qt.CursorShape.ArrowCursor

        self.setCursor(cursor)

    def toggle_grid(self, _val):
        self.do_draw()

    def do_draw(self, force_draw: bool = False):
        self.api.art.canvas.do_draw(force_draw)
        self.ui.canvas_container_size = (
            self.ui.canvas_container.viewport().size()
        )
