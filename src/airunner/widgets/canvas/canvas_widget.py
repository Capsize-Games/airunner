from typing import Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QPoint

from airunner.cursors.circle_brush import CircleCursor
from airunner.enums import SignalCode, CanvasToolName
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.mixins.clipboard_handler_mixin import ClipboardHandlerMixin
from airunner.widgets.canvas.mixins.grid_handler_mixin import GridHandlerMixin
from airunner.widgets.canvas.mixins.image_handler_mixin import ImageHandlerMixin
from airunner.widgets.canvas.templates.canvas_ui import Ui_canvas
from airunner.workers.image_data_worker import ImageDataWorker


class CanvasWidget(
    BaseWidget,
    GridHandlerMixin,
    ImageHandlerMixin,
    ClipboardHandlerMixin
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
        GridHandlerMixin.__init__(self)
        ImageHandlerMixin.__init__(self)
        ClipboardHandlerMixin.__init__(self)
        super().__init__(*args, **kwargs)
        self._startPos = QPoint(0, 0)
        self.images = {}
        self.active_grid_area_pivot_point = QPoint(0, 0)
        self.active_grid_area_position = QPoint(0, 0)
        self.current_image_index = 0
        self.draggable_pixmaps_in_scene = {}
        self.grid_settings: dict = {}
        self.active_grid_settings: dict = {}
        self.canvas_settings: dict = {}
        self.drag_pos: QPoint = Optional[None]
        self._grid_settings = {}
        self._canvas_settings = {}
        self._active_grid_settings = {}
        self.image_data_worker = None
        self.canvas_resize_worker = None
        self.signal_handlers = {
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL: self.apply_filter,
        }
        self.worker_class_map = {
            "image_data_worker": ImageDataWorker,
        }

    @property
    def image_pivot_point(self):
        settings = self.settings
        try:
            return QPoint(
                settings["pivot_point_x"],
                settings["pivot_point_y"]
            )
        except Exception as e:
            self.logger.error(e)
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        settings = self.settings
        settings["pivot_point_x"] = value.x()
        settings["pivot_point_y"] = value.y()
        self.settings = settings

    def on_canvas_update_cursor_signal(self, message: dict):
        settings = self.settings
        event = message["event"]
        if settings["current_tool"] in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER
        ):
            cursor = CircleCursor(
                Qt.GlobalColor.white,
                Qt.GlobalColor.transparent,
                settings["brush_settings"]["size"],
            )
        elif settings["current_tool"] is CanvasToolName.ACTIVE_GRID_AREA:
            if event.buttons() == Qt.MouseButton.LeftButton:
                cursor = Qt.CursorShape.ClosedHandCursor
            else:
                cursor = Qt.CursorShape.OpenHandCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor
        self.setCursor(cursor)

    def toggle_grid(self, val):
        self.do_draw()
    
    def wheelEvent(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers in [
            Qt.KeyboardModifier.ControlModifier,
            Qt.KeyboardModifier.ShiftModifier,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ]:
            self.update_grid_dimensions_based_on_event(event)
            self.do_draw()
        else:
            super().wheelEvent(event)  # Propagate the event to the base class if no modifier keys are pressed

    def showEvent(self, event):
        super().showEvent(event)
        self.do_draw(force_draw=True)

    def initialize_form(self):
        settings = self.settings

        self.ui.drawing_pad_groupbox.blockSignals(True)
        self.ui.drawing_pad_groupbox.checked = settings["drawing_pad_settings"]["enabled"]
        self.ui.drawing_pad_groupbox.blockSignals(False)

    def do_draw(
        self,
        force_draw: bool = False
    ):
        self.emit_signal(SignalCode.SCENE_DO_DRAW_SIGNAL, {
            "force_draw": force_draw
        })
        self.ui.canvas_container_size = self.ui.canvas_container.viewport().size()

    def save_image(self, image_path, image=None):
        self.save_image(image_path, image, self.scene.items())
