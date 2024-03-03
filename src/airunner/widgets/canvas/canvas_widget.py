import base64
import io
from typing import Optional

from PIL import Image, ImageFilter
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QPoint, QRect

from airunner.cursors.circle_brush import CircleCursor
from airunner.enums import SignalCode, ServiceCode, CanvasToolName, GeneratorSection
from airunner.service_locator import ServiceLocator
from airunner.settings import AVAILABLE_IMAGE_FILTERS
from airunner.utils import convert_base64_to_image
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.clipboard_handler import ClipboardHandler
from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap
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
        self.drag_pos: QPoint = None

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
            SignalCode.SD_IMAGE_GENERATED_SIGNAL: self.on_image_generated_signal,
            SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL: self.on_load_image_from_path,
            SignalCode.CANVAS_HANDLE_LAYER_CLICK_SIGNAL: self.on_canvas_handle_layer_click_signal,
            SignalCode.CANVAS_UPDATE_SIGNAL: self.on_update_canvas_signal,
            SignalCode.LAYER_SET_CURRENT_SIGNAL: self.on_set_current_layer_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.CANVAS_PASTE_IMAGE_SIGNAL: self.on_canvas_paste_image_signal,
            SignalCode.CANVAS_COPY_IMAGE_SIGNAL: self.on_canvas_copy_image_signal,
            SignalCode.CANVAS_CUT_IMAGE_SIGNAL: self.on_canvas_cut_image_signal,
            SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL: self.on_canvas_rotate_90_clockwise_signal,
            SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL: self.on_canvas_rotate_90_counter_clockwise_signal,
            SignalCode.CANVAS_CANCEL_FILTER_SIGNAL: self.cancel_filter,
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL: self.apply_filter,
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL: self.preview_filter,
        }

        # Map service codes to class functions
        self.services = {
            ServiceCode.CURRENT_ACTIVE_IMAGE: self.current_active_image,
            ServiceCode.CURRENT_LAYER: self.current_layer,
        }

        # Map class properties to worker classes
        self.worker_class_map = {
            "image_data_worker": ImageDataWorker,
            "canvas_resize_worker": CanvasResizeWorker
        }

        self.image_handler = ImageHandler()
        self.grid_handler = GridHandler()
        self.clipboard_handler = ClipboardHandler()

    @property
    def image_pivot_point(self):
        try:
            layer = ServiceLocator.get(ServiceCode.CURRENT_LAYER)()
            return QPoint(layer["pivot_point_x"], layer["pivot_point_y"])
        except Exception as e:
            self.logger.error(e)
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        self.emit(SignalCode.LAYER_UPDATE_CURRENT_SIGNAL, {
            "pivot_point_x": value.x(),
            "pivot_point_y": value.y()
        })

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

    @property
    def current_layer(self):
        layer_index: int = self.settings["current_layer_index"]
        return self.settings["layers"][layer_index]

    def current_active_image(self) -> Image:
        layer = self.current_layer
        base_64_image = layer["base_64_image"]
        return convert_base64_to_image(base_64_image)

    def set_current_active_image(self, value: Image):
        self.add_image_to_current_layer(value)

    def on_canvas_paste_image_signal(self, _event):
        self.paste_image_from_clipboard()

    def on_canvas_copy_image_signal(self, _event):
        self.copy_image(self.current_active_image())

    def on_canvas_cut_image_signal(self, _event):
        self.cut_image()

    def on_canvas_rotate_90_clockwise_signal(self, _event):
        self.rotate_90_clockwise()

    def on_canvas_rotate_90_counter_clockwise_signal(self, _event):
        self.rotate_90_counterclockwise()

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
        elif self.settings["current_tool"] is CanvasToolName.ACTIVE_GRID_AREA:
            if event.buttons() == Qt.MouseButton.LeftButton:
                cursor = Qt.CursorShape.ClosedHandCursor
            else:
                cursor = Qt.CursorShape.OpenHandCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor
        self.setCursor(cursor)

    def on_set_current_layer_signal(self, args):
        self.set_current_layer(args)

    def on_update_canvas_signal(self, _ignore):
        self.update()

    def set_current_layer(self, args):
        index, current_layer_index = args
        item = self.ui.container.layout().itemAt(current_layer_index)
        if item:
            item.widget().frame.setStyleSheet(self.css("layer_normal_style"))
        if self.ui.container:
            item = self.ui.container.layout().itemAt(index)
            if item:
                item.widget().frame.setStyleSheet(self.css("layer_highlight_style"))

    def canvas_drag_pos(self):
        return self.drag_pos

    def on_canvas_handle_layer_click_signal(self, data):
        layer = data["layer"]
        index = data["index"]
        current_layer_index = data["current_layer_index"]
        selected_layers = data["selected_layers"]
        if self.ui.container:
            if index in selected_layers:
                widget = selected_layers[index].layer_widget
                if widget and index != current_layer_index:
                    del selected_layers[index]
            else:
                item = self.ui.container.layout().itemAt(index)
                if item and index != current_layer_index:
                    selected_layers[index] = layer
    
    def on_canvas_do_draw_signal(self, force_draw: bool = False):
        self.do_draw(force_draw=force_draw)

    def on_image_generated_signal(self, image_data: dict):
        if not image_data or image_data["images"] is None:
            return
        self.add_image_to_scene(
            image_data["images"][0],
            is_outpaint=image_data["data"]["action"] == GeneratorSection.OUTPAINT.value,
            outpaint_box_rect=image_data["data"]["options"]["outpaint_box_rect"]
        )

    def on_canvas_resize_worker_response_signal(self, data: dict):
        force_draw = data["force_draw"]
        do_draw_layers = data["do_draw_layers"]
        lines_data = data["lines_data"]
        self.emit(SignalCode.CANVAS_CLEAR_LINES_SIGNAL)
        draw_grid = self.settings["grid_settings"]["show_grid"]
        if not draw_grid:
            return

        ServiceLocator.get(ServiceCode.CANVAS_REGISTER_LINE_DATA)(lines_data)

        self.do_draw(
            force_draw=force_draw,
            do_draw_layers=do_draw_layers
        )

    def on_image_data_worker_response_signal(self, message):
        self.emit(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL)
        self.emit(SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL)
        nsfw_content_detected = message["nsfw_content_detected"]
        path = message["path"]
        if nsfw_content_detected and self.settings["nsfw_filter"]:
            self.emit(SignalCode.LOG_ERROR_SIGNAL, "Explicit content detected, try again.")
        self.emit(SignalCode.LAYERS_SHOW_SIGNAL)
        if path is not None:
            self.emit(
                SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
                f"Image generated to {path}"
            )

    def on_application_settings_changed_signal(self):
        if (
            self.grid_settings_changed() or
            self.active_grid_settings_changed() or
            self.canvas_settings_changed()
        ):
            self.emit(SignalCode.CANVAS_DO_RESIZE_SIGNAL, {
                "force_draw": True
            })

    def on_load_image_from_path(self, image_path):
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self.load_image_from_object(image)

    def current_image(self):
        image = None
        try:
            image = self.get_service(ServiceCode.GET_IMAGE_FROM_LAYER)()
        except IndexError:
            pass
        return image

    def current_line_image(self):
        line_image = None
        try:
            line_image = self.get_service(ServiceCode.GET_LINE_IMAGE_FROM_LAYER)()
        except IndexError:
            pass
        return line_image
    
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
                        self.emit(SignalCode.SET_CANVAS_COLOR_SIGNAL)
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
            self.emit(SignalCode.CANVAS_DO_RESIZE_SIGNAL)
        self.emit(
            SignalCode.SCENE_RESIZE_SIGNAL,
            self.size()
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.do_draw(force_draw=True)

    def add_image_to_current_layer(self, image: Image):
        self.logger.debug("Adding image to current layer")
        layer_index: int = self.settings["current_layer_index"]
        base_64_image: Optional[bytes] = None

        try:
            if image:
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                base_64_image = base64.b64encode(buffered.getvalue())
        except Exception as e:
            self.logger.error(e)

        if base_64_image is not None:
            settings = self.settings
            settings["layers"][layer_index]["base_64_image"] = base_64_image
            self.settings = settings

    def action_button_clicked_focus(self):
        self.last_pos = QPoint(0, 0)
        self.do_draw()
    
    def do_draw(
        self,
        force_draw: bool = False,
        do_draw_layers: bool = None
    ):
        self.emit(SignalCode.SCENE_DO_DRAW_SIGNAL, {
            "force_draw": force_draw,
            "do_draw_layers": do_draw_layers
        })
        self.ui.canvas_container_size = self.ui.canvas_container.viewport().size()
        self.ui.canvas_position.setText(
            f"X {-self.settings['canvas_settings']['pos_x']: 05d} Y {self.settings['canvas_settings']['pos_y']: 05d}"
        )
    
    def handle_outpaint(self, outpaint_box_rect, outpainted_image, action=None) -> [Image, QPoint, QPoint]:
        if self.current_active_image() is None:
            point = QPoint(outpaint_box_rect.x(), outpaint_box_rect.y())
            return outpainted_image, QPoint(0, 0), point

        # make a copy of the current canvas image
        existing_image_copy = self.current_active_image().copy()
        width = existing_image_copy.width
        height = existing_image_copy.height

        pivot_point = self.image_pivot_point
        root_point = QPoint(0, 0)
        layer = ServiceLocator.get(ServiceCode.CURRENT_LAYER)()
        current_image_position = QPoint(layer["pos_x"], layer["pos_y"])

        is_drawing_left = outpaint_box_rect.x() < current_image_position.x()
        is_drawing_right = outpaint_box_rect.x() > current_image_position.x()
        is_drawing_up = outpaint_box_rect.y() < current_image_position.y()
        is_drawing_down = outpaint_box_rect.y() > current_image_position.y()

        if is_drawing_down:
            height += outpaint_box_rect.y()
        if is_drawing_right:
            width += outpaint_box_rect.x()
        if is_drawing_up:
            height += current_image_position.y()
            root_point.setY(outpaint_box_rect.y())
        if is_drawing_left:
            width += current_image_position.x()
            root_point.setX(outpaint_box_rect.x())

        new_dimensions = (width, height)

        new_image = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_a = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_b = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))

        image_root_point = QPoint(root_point.x(), root_point.y())
        image_pivot_point = QPoint(pivot_point.x(), pivot_point.y())

        new_image_a.paste(outpainted_image, (int(outpaint_box_rect.x()), int(outpaint_box_rect.y())))
        new_image_b.paste(existing_image_copy, (current_image_position.x(), current_image_position.y()))

        if action == GeneratorSection.OUTPAINT.value:
            new_image = Image.alpha_composite(new_image, new_image_a)
            new_image = Image.alpha_composite(new_image, new_image_b)
        else:
            new_image = Image.alpha_composite(new_image, new_image_b)
            new_image = Image.alpha_composite(new_image, new_image_a)

        return new_image, image_root_point, image_pivot_point
    
    def load_image_from_object(
        self,
        image: Image,
        is_outpaint: bool = False
    ):
        self.add_image_to_scene(
            image_data=dict(
                image=image
            ), 
            is_outpaint=is_outpaint
        )

    @staticmethod
    def current_draggable_pixmap():
        return ServiceLocator.get(ServiceCode.CURRENT_DRAGGABLE_PIXMAP)()
        
    def copy_image(
        self,
        image: Image = None
    ) -> object:
        return self.clipboard_handler.copy_image(
            image,
            self.current_draggable_pixmap()
        )

    def cut_image(self):
        draggable_pixmap: DraggablePixmap = self.clipboard_handler.cut_image()
        if draggable_pixmap:
            self.emit(SignalCode.REMOVE_SCENE_ITEM_SIGNAL, draggable_pixmap)
            self.emit(SignalCode.LAYER_DELETE_CURRENT_SIGNAL)
            self.update()
    
    def delete_image(self):
        self.logger.debug("Deleting image from canvas")
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.remove_scene_item(draggable_pixmap)
        self.update()
    
    def paste_image_from_clipboard(self):
        image = self.clipboard_handler.paste_image_from_clipboard()
        self.create_image(image)

    def create_image(self, image):
        if self.settings["resize_on_paste"]:
            image = self.resize_image(image)
        self.add_image_to_scene(image)
    
    def resize_image(self, image):
        image.thumbnail(
            (
                self.settings["is_maximized"],
                self.settings["working_height"]
            ),
            Image.ANTIALIAS
        )
        return image

    def remove_current_draggable_pixmap_from_scene(self):
        current_draggable_pixmap = self.current_draggable_pixmap()
        if current_draggable_pixmap:
            self.remove_scene_item(current_draggable_pixmap)
    
    def switch_to_layer(self, layer_index):
        self.emit(SignalCode.LAYER_SWITCH_SIGNAL, layer_index)

    def add_image_to_scene(
        self,
        image: Image,
        is_outpaint: bool = False,
        outpaint_box_rect: QPoint = None
    ):
        """
        Adds a given image to the scene
        :param image_data: dict containing the image to be added to the scene
        :param is_outpaint: bool indicating if the image is an outpaint
        :param outpaint_box_rect: QPoint indicating the root point of the image
        :return:
        """
        self.do_draw_layers = True

        if not is_outpaint:
            self.set_current_active_image(image)
            self.do_draw(
                force_draw=True,
                do_draw_layers=True
            )
        else:
            image, root_point, pivot_point = self.handle_outpaint(
                outpaint_box_rect,
                image,
                action=GeneratorSection.OUTPAINT.value
            )
            self.set_current_active_image(image)
            self.do_draw(
                force_draw=True,
                do_draw_layers=True
            )
    
    @staticmethod
    def filter_with_filter(filter_object: ImageFilter.Filter):
        return type(filter_object).__name__ in AVAILABLE_IMAGE_FILTERS

    def load_image(self, image_path: str):
        image = self.image_handler.load_image(image_path)
        self.add_image_to_scene(image)

    def save_image(self, image_path, image=None):
        self.image_handler.save_image(image_path, image, self.scene.items())

    def rotate_90_clockwise(self):
        self.rotate_image(Image.ROTATE_270)

    def rotate_90_counterclockwise(self):
        self.rotate_image(Image.ROTATE_90)

    def rotate_image(self, angle):
        image = self.image_handler.rotate_image(
            angle,
            self.current_active_image()
        )
        self.set_current_active_image(image)
        self.emit(SignalCode.CANVAS_DO_RESIZE_SIGNAL, {
            "force_draw": True,
            "do_draw_layers": True
        })

    def apply_filter(self, _filter_object: ImageFilter.Filter):
        self.image_handler.apply_filter(_filter_object)

    def cancel_filter(self):
        image = self.image_handler.cancel_filter()
        if image:
            self.load_image_from_object(image=image)

    def preview_filter(self, filter_object: ImageFilter.Filter):
        filtered_image = self.image_handler.preview_filter(
            self.current_image(),
            filter_object
        )
        self.load_image_from_object(image=filtered_image)

    def cell_size_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()

    def line_width_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()

    def line_color_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()
