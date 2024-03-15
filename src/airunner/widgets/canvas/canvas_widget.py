from typing import Optional

from PIL import ImageFilter
from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QPoint, QRect

from airunner.cursors.circle_brush import CircleCursor
from airunner.enums import SignalCode, ServiceCode, CanvasToolName
from airunner.service_locator import ServiceLocator
from airunner.settings import AVAILABLE_IMAGE_FILTERS
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.clipboard_handler import ClipboardHandler
from airunner.widgets.canvas.grid_handler import GridHandler
from airunner.widgets.canvas.image_handler import ImageHandler
from airunner.widgets.canvas.templates.canvas_ui import Ui_canvas
from airunner.workers.canvas_resize_worker import CanvasResizeWorker
from airunner.workers.image_data_worker import ImageDataWorker


class CanvasWidget(BaseWidget):
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
        self.redraw_lines = False
        self.grid_settings: dict = {}
        self.active_grid_settings: dict = {}
        self.canvas_settings: dict = {}
        self.drag_pos: QPoint = Optional[None]

        self._grid_settings = {}
        self._canvas_settings = {}
        self._active_grid_settings = {}

        self.ui.central_widget.resizeEvent = self.resizeEvent

        self.image_data_worker = None
        self.canvas_resize_worker = None

        # Map signal codes to class function slots
        self.signal_handlers = {
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
            SignalCode.CANVAS_DO_DRAW_SIGNAL: self.on_canvas_do_draw_signal,
            SignalCode.SD_IMAGE_DATA_WORKER_RESPONSE_SIGNAL: self.on_image_data_worker_response_signal,
            SignalCode.CANVAS_RESIZE_WORKER_RESPONSE_SIGNAL: self.on_canvas_resize_worker_response_signal,
            SignalCode.CANVAS_UPDATE_SIGNAL: self.on_update_canvas_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL: self.apply_filter,
        }

        # Map class properties to worker classes
        self.worker_class_map = {
            "image_data_worker": ImageDataWorker,
            "canvas_resize_worker": CanvasResizeWorker
        }

        self.image_handler = ImageHandler()
        self.grid_handler = GridHandler()
        self.clipboard_handler = ClipboardHandler()

        self.ui.controlnet_groupbox.blockSignals(True)
        self.ui.drawing_pad_groupbox.blockSignals(True)
        self.ui.controlnet_groupbox.checked = self.settings["generator_settings"]["enable_controlnet"]
        self.ui.drawing_pad_groupbox.checked = self.settings["drawing_pad_settings"]["enabled"]
        self.ui.controlnet_groupbox.blockSignals(False)
        self.ui.drawing_pad_groupbox.blockSignals(False)

    @property
    def image_pivot_point(self):
        try:
            return QPoint(
                self.settings["pivot_point_x"],
                self.settings["pivot_point_y"]
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

    @property
    def active_grid_area_rect(self):
        settings = self.settings
        rect = QRect(
            settings["active_grid_settings"]["pos_x"],
            settings["active_grid_settings"]["pos_y"],
            settings["active_grid_settings"]["width"],
            settings["active_grid_settings"]["height"]
        )

        # apply self.pos_x and self.pox_y to the rect
        rect.translate(
            self.settings["canvas_settings"]["pos_x"],
            self.settings["canvas_settings"]["pos_y"]
        )

        return rect

    def toggle_controlnet(self, val):
        settings = self.settings
        settings["generator_settings"]["enable_controlnet"] = val
        self.settings = settings

    def toggle_drawing_pad(self, val):
        settings = self.settings
        settings["drawing_pad_settings"]["enabled"] = val
        self.settings = settings

    def on_canvas_update_cursor_signal(self, event):
        if self.settings["current_tool"] in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER
        ):
            cursor = CircleCursor(
                Qt.GlobalColor.white,
                Qt.GlobalColor.transparent,
                self.settings["brush_settings"]["size"],
            )
            self.setCursor(cursor)
        elif self.settings["current_tool"] is CanvasToolName.ACTIVE_GRID_AREA:
            # if event.buttons() == Qt.MouseButton.LeftButton:
            #     cursor = Qt.CursorShape.ClosedHandCursor
            # else:
            #     cursor = Qt.CursorShape.OpenHandCursor
            pass
        else:
            cursor = Qt.CursorShape.ArrowCursor
            self.setCursor(cursor)

    def on_update_canvas_signal(self, _ignore):
        self.update()

    def canvas_drag_pos(self):
        return self.drag_pos

    def on_canvas_do_draw_signal(self, force_draw: bool = False):
        self.do_draw(force_draw=force_draw)

    def on_canvas_resize_worker_response_signal(self, data: dict):
        force_draw = data["force_draw"]
        do_draw_layers = data["do_draw_layers"]
        lines_data = data["lines_data"]
        self.emit_signal(SignalCode.CANVAS_CLEAR_LINES_SIGNAL)
        draw_grid = self.settings["grid_settings"]["show_grid"]
        if not draw_grid:
            return

        ServiceLocator.get(ServiceCode.CANVAS_REGISTER_LINE_DATA)(lines_data)

        self.do_draw(
            force_draw=force_draw,
            do_draw_layers=do_draw_layers
        )

    def on_image_data_worker_response_signal(self, message):
        self.emit_signal(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL)
        self.emit_signal(SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL)
        nsfw_content_detected = message["nsfw_content_detected"]
        path = message["path"]
        if nsfw_content_detected and self.settings["nsfw_filter"]:
            self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, "Explicit content detected, try again.")
        if path is not None:
            self.emit_signal(
                SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                f"Image generated to {path}"
            )

    def on_application_settings_changed_signal(self):
        if (
            self.grid_settings_changed() or
            self.active_grid_settings_changed() or
            self.canvas_settings_changed()
        ):
            self.emit_signal(SignalCode.CANVAS_DO_RESIZE_SIGNAL, {
                "force_draw": True
            })
    
    def toggle_grid(self, val):
        self.do_draw()
    
    def wheelEvent(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers in [
            Qt.KeyboardModifier.ControlModifier,
            Qt.KeyboardModifier.ShiftModifier,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ]:
            self.grid_handler.update_grid_dimensions_based_on_event(event)
            self.do_draw()
        else:
            super().wheelEvent(event)  # Propagate the event to the base class if no modifier keys are pressed

    def grid_settings_changed(self) -> bool:
        changed = False
        settings = self.settings
        if "grid_settings" in settings:
            grid_settings = settings["grid_settings"]
            for k, v in grid_settings.items():
                if k not in self._grid_settings or self._grid_settings[k] != v:
                    self._grid_settings[k] = v
                    if k == "canvas_color":
                        self.emit_signal(SignalCode.SET_CANVAS_COLOR_SIGNAL)
                    elif k in ["line_color", "cell_size", "line_width"]:
                        self.redraw_lines = True
                    changed = True
        return changed

    def active_grid_settings_changed(self) -> bool:
        changed = False
        settings = self.settings
        if "active_grid_settings" in settings:
            active_grid_settings = self.settings["active_grid_settings"]
            for k, v in active_grid_settings.items():
                if k not in self._active_grid_settings or self._active_grid_settings[k] != v:
                    self._active_grid_settings[k] = v
                    if k in ["pos_x", "pos_y", "width", "height"]:
                        self.redraw_lines = True
                    changed = True
        return changed

    def canvas_settings_changed(self) -> bool:
        changed = False
        settings = self.settings
        if "canvas_settings" in settings:
            canvas_settings = self.settings["canvas_settings"]
            for k, v in canvas_settings.items():
                if k not in self._canvas_settings or self._canvas_settings[k] != v:
                    self._canvas_settings[k] = v
                    changed = True
        return changed

    def resizeEvent(self, event):
        if self.ui.canvas_container:
            self.emit_signal(SignalCode.CANVAS_DO_RESIZE_SIGNAL)
        self.emit_signal(
            SignalCode.SCENE_RESIZE_SIGNAL,
            self.size()
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.do_draw(force_draw=True)

    def action_button_clicked_focus(self):
        self.last_pos = QPoint(0, 0)
        self.do_draw()
    
    def do_draw(
        self,
        force_draw: bool = False,
        do_draw_layers: bool = None
    ):
        self.emit_signal(SignalCode.SCENE_DO_DRAW_SIGNAL, {
            "force_draw": force_draw,
            "do_draw_layers": do_draw_layers
        })
        self.ui.canvas_container_size = self.ui.canvas_container.viewport().size()
        self.ui.canvas_position.setText(
            f"X {-self.settings['canvas_settings']['pos_x']: 05d} Y {self.settings['canvas_settings']['pos_y']: 05d}"
        )

    @staticmethod
    def filter_with_filter(filter_object: ImageFilter.Filter):
        return type(filter_object).__name__ in AVAILABLE_IMAGE_FILTERS

    def save_image(self, image_path, image=None):
        self.image_handler.save_image(image_path, image, self.scene.items())

    def apply_filter(self, _filter_object: ImageFilter.Filter):
        self.image_handler.apply_filter(_filter_object)

    def cell_size_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()

    def line_width_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()

    def line_color_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()
