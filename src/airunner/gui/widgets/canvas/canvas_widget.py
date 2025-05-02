from typing import Optional

from PySide6.QtCore import Qt, QPoint, QTimer
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
        self.emit_signal(SignalCode.RECENTER_GRID_SIGNAL)

    @Slot()
    def on_new_button_clicked(self):
        self.emit_signal(SignalCode.CANVAS_CLEAR)

    @Slot()
    def on_import_button_clicked(self):
        self.emit_signal(SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL)

    @Slot()
    def on_export_button_clicked(self):
        self.emit_signal(SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL)

    @Slot()
    def on_undo_button_clicked(self):
        self.emit_signal(SignalCode.UNDO_SIGNAL)

    @Slot()
    def on_redo_button_clicked(self):
        self.emit_signal(SignalCode.REDO_SIGNAL)

    @Slot(bool)
    def on_grid_button_toggled(self, val: bool):
        self.update_grid_settings("show_grid", val)

    @Slot(bool)
    def on_brush_button_toggled(self, val: bool):
        self.emit_signal(
            SignalCode.TOGGLE_TOOL,
            {"tool": CanvasToolName.BRUSH, "active": val},
        )

    @Slot(bool)
    def on_eraser_button_toggled(self, val: bool):
        self.emit_signal(
            SignalCode.TOGGLE_TOOL,
            {"tool": CanvasToolName.ERASER, "active": val},
        )

    @Slot(bool)
    def on_active_grid_area_button_toggled(self, val: bool):
        self.emit_signal(
            SignalCode.TOGGLE_TOOL,
            {"tool": CanvasToolName.ACTIVE_GRID_AREA, "active": val},
        )

    def on_toggle_tool_signal(self, message: dict):
        tool = message.get("tool", None)
        active = message.get("active", False)
        self._update_action_buttons(tool, active)
        self.emit_signal(SignalCode.CANVAS_UPDATE_CURSOR)

    def on_toggle_grid_signal(self, message: dict):
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
            QTimer.singleShot(100, lambda: self.do_draw(force_draw=True))
            self.emit_signal(SignalCode.CANVAS_UPDATE_CURSOR)

    def on_canvas_update_cursor_signal(self, message: dict):
        event = message.get("event", None)
        cursor = None
        if message.get("apply_cursor", None):
            if self.current_tool in (
                CanvasToolName.BRUSH,
                CanvasToolName.ERASER,
            ):
                cursor = circle_cursor(
                    Qt.GlobalColor.white,
                    Qt.GlobalColor.transparent,
                    self.brush_settings.size,
                )
            elif self.current_tool is CanvasToolName.ACTIVE_GRID_AREA:
                if event and event.buttons() == Qt.MouseButton.LeftButton:
                    cursor = Qt.CursorShape.ClosedHandCursor
                else:
                    cursor = Qt.CursorShape.OpenHandCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor

        if cursor:
            self.setCursor(cursor)

    def toggle_grid(self, _val):
        self.do_draw()

    def do_draw(self, force_draw: bool = False):
        self.emit_signal(
            SignalCode.SCENE_DO_DRAW_SIGNAL, {"force_draw": force_draw}
        )
        self.ui.canvas_container_size = (
            self.ui.canvas_container.viewport().size()
        )
