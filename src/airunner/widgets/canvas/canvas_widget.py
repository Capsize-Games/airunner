from typing import Optional

from PySide6.QtCore import Qt, QPoint, QTimer

from airunner.cursors.circle_brush import CircleCursor
from airunner.enums import SignalCode, CanvasToolName
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.templates.canvas_ui import Ui_canvas


class CanvasWidget(
    BaseWidget
):
    """
    Widget responsible for multiple functionalities:

    - Allows the user to draw on a canvas.
    - Displays the grid.
    - Displays images.
    - Handles the active grid area.
    """
    widget_class_ = Ui_canvas

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._startPos = QPoint(0, 0)
        self.images = {}
        self.active_grid_area_pivot_point = QPoint(0, 0)
        self.active_grid_area_position = QPoint(0, 0)
        self.current_image_index = 0
        self.draggable_pixmaps_in_scene = {}
        self.drag_pos: QPoint = Optional[None]
        self._grid_settings = {}
        self._active_grid_settings = {}
        self.signal_handlers = {
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
        }

    @property
    def image_pivot_point(self):
        settings = self.application_settings
        try:
            return QPoint(
                settings.pivot_point_x,
                settings.pivot_point_y
            )
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

    def on_canvas_update_cursor_signal(self, message: dict):
        event = message.get("event", None)
        if self.current_tool in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER
        ):
            cursor = CircleCursor(
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
        self.setCursor(cursor)

    def toggle_grid(self, val):
        self.do_draw()

    def showEvent(self, event):
        super().showEvent(event)
        # Delay the initial draw slightly to ensure viewport is properly sized
        QTimer.singleShot(100, lambda: self.do_draw(force_draw=True))

    def do_draw(
        self,
        force_draw: bool = False
    ):
        self.emit_signal(SignalCode.SCENE_DO_DRAW_SIGNAL, {
            "force_draw": force_draw
        })
        self.ui.canvas_container_size = self.ui.canvas_container.viewport().size()
