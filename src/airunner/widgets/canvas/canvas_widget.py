import base64
import io
from functools import partial

from PIL import Image, ImageFilter
from PIL.ImageQt import ImageQt
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QBrush, QColor, QPixmap
from PyQt6.QtWidgets import QGraphicsItemGroup, QGraphicsItem, QGraphicsView

from airunner.cursors.circle_brush import CircleCursor
from airunner.enums import SignalCode, ServiceCode, CanvasToolName, GeneratorSection
from airunner.service_locator import ServiceLocator
from airunner.settings import AVAILABLE_IMAGE_FILTERS
from airunner.utils import apply_opacity_to_image
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.clipboard_handler import ClipboardHandler
from airunner.widgets.canvas.custom_scene import CustomScene
from airunner.widgets.canvas.draggables import DraggablePixmap, ActiveGridArea
from airunner.widgets.canvas.grid_handler import GridHandler
from airunner.widgets.canvas.image_handler import ImageHandler
from airunner.widgets.canvas.templates.canvas_ui import Ui_canvas
from airunner.widgets.canvas.zoom_handler import ZoomHandler
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
        self.scene = None
        self.ui.canvas_container_size = None
        self.images = {}
        self.active_grid_area = None
        self.active_grid_area_pivot_point = QPoint(0, 0)
        self.active_grid_area_position = QPoint(0, 0)
        self.last_pos = QPoint(0, 0)
        self.current_image_index = 0
        self.draggable_pixmaps_in_scene = {}
        self.initialized = False
        self.drawing = False
        self.redraw_lines = False
        self.has_lines = False
        self.line_group = QGraphicsItemGroup()
        self.grid_settings: dict = {}
        self.active_grid_settings: dict = {}
        self.canvas_settings: dict = {}
        self.drag_pos: QPoint = None
        self.do_draw_layers = True

        self._grid_settings = {}
        self._canvas_settings = {}
        self._active_grid_settings = {}
        self.pixmaps = {}

        self.ui.central_widget.resizeEvent = self.resizeEvent
        self.ui.canvas_container.resizeEvent = self.window_resized

        self.image_data_worker = None
        self.canvas_resize_worker = None

        # Map signal codes to class function slots
        self.signal_handlers = {
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
            SignalCode.CANVAS_DO_DRAW_SIGNAL: self.on_canvas_do_draw_signal,
            SignalCode.CANVAS_CLEAR_LINES_SIGNAL: self.on_canvas_clear_lines_signal,
            SignalCode.SD_IMAGE_DATA_WORKER_RESPONSE_SIGNAL: self.on_image_data_worker_response_signal,
            SignalCode.CANVAS_RESIZE_WORKER_RESPONSE_SIGNAL: self.on_canvas_resize_worker_response_signal,
            SignalCode.SD_IMAGE_GENERATED_SIGNAL: self.on_image_generated_signal,
            SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL: self.on_load_image_from_path,
            SignalCode.CANVAS_HANDLE_LAYER_CLICK_SIGNAL: self.on_canvas_handle_layer_click_signal,
            SignalCode.CANVAS_UPDATE_SIGNAL: self.on_update_canvas_signal,
            SignalCode.LAYER_SET_CURRENT_SIGNAL: self.on_set_current_layer_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.CANVAS_CLEAR: self.on_canvas_clear_signal,
            SignalCode.CANVAS_PASTE_IMAGE_SIGNAL: self.on_canvas_paste_image_signal,
            SignalCode.CANVAS_COPY_IMAGE_SIGNAL: self.on_canvas_copy_image_signal,
            SignalCode.CANVAS_CUT_IMAGE_SIGNAL: self.on_canvas_cut_image_signal,
            SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL: self.on_canvas_rotate_90_clockwise_signal,
            SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL: self.on_canvas_rotate_90_counter_clockwise_signal,
            SignalCode.CANVAS_CANCEL_FILTER_SIGNAL: self.cancel_filter,
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL: self.apply_filter,
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL: self.preview_filter,
            SignalCode.CANVAS_ZOOM_LEVEL_CHANGED: self.on_zoom_level_changed_signal,
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_tool_changed_signal,
        }

        # Map service codes to class functions
        self.services = {
            ServiceCode.CURRENT_ACTIVE_IMAGE: self.canvas_current_active_image,
            ServiceCode.CURRENT_LAYER: self.canvas_current_active_image,
        }

        # Map class properties to worker classes
        self.worker_class_map = {
            "image_data_worker": ImageDataWorker,
            "canvas_resize_worker": CanvasResizeWorker
        }

        self.image_handler = ImageHandler()
        self.grid_handler = GridHandler()
        self.clipboard_handler = ClipboardHandler()
        self.zoom_handler = ZoomHandler()

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
        rect.translate(self.settings["canvas_settings"]["pos_x"], self.settings["canvas_settings"]["pos_y"])

        return rect

    @property
    def current_active_image(self):
        return self.get_service(ServiceCode.CURRENT_ACTIVE_IMAGE)()

    @current_active_image.setter
    def current_active_image(self, value):
        self.add_image_to_current_layer(value)

    def on_canvas_paste_image_signal(self, _event):
        self.paste_image_from_clipboard()

    def on_canvas_copy_image_signal(self, _event):
        self.copy_image(ServiceLocator.get(ServiceCode.CURRENT_ACTIVE_IMAGE)())

    def on_canvas_cut_image_signal(self, _event):
        self.cut_image()

    def on_canvas_rotate_90_clockwise_signal(self, _event):
        self.rotate_90_clockwise()

    def on_canvas_rotate_90_counter_clockwise_signal(self, _event):
        self.rotate_90_counterclockwise()

    def on_canvas_update_cursor_signal(self, event):
        if self.settings["current_tool"] in [CanvasToolName.BRUSH, CanvasToolName.ERASER]:
            self.setCursor(CircleCursor(
                Qt.GlobalColor.white,
                Qt.GlobalColor.transparent,
                self.settings["brush_settings"]["size"],
            ))
        elif self.settings["current_tool"] is CanvasToolName.ACTIVE_GRID_AREA:
            if event.buttons() == Qt.MouseButton.LeftButton:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def on_zoom_level_changed_signal(self):
        transform = self.zoom_handler.on_zoom_level_changed()

        # Set the transform
        self.ui.canvas_container.setTransform(transform)

        # Redraw lines
        self.emit(SignalCode.CANVAS_DO_DRAW_SIGNAL)

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

    def canvas_current_active_image(self):
        return self.current_active_image
    
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
    
    def on_canvas_clear_lines_signal(self):
        self.clear_lines()

    def on_canvas_do_draw_signal(self, force_draw: bool = False):
        self.do_draw(force_draw=force_draw)

    def on_image_generated_signal(self, image_data: dict):
        self.add_image_to_scene(image_data["images"][0])

    def on_canvas_resize_worker_response_signal(self, data: dict):
        force_draw = data["force_draw"]
        do_draw_layers = data["do_draw_layers"]
        lines_data = data["lines_data"]
        self.clear_lines()
        draw_grid = self.settings["grid_settings"]["show_grid"]
        if not draw_grid:
            return
        for line_data in lines_data:
            try:
                line = self.scene.addLine(*line_data)
                self.line_group.addToGroup(line)
            except TypeError as e:
                self.logger.error(f"TypeError: {e}")
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
            self.do_resize_canvas(force_draw=True)

    def on_main_window_loaded_signal(self):
        self.initialized = True

    def on_tool_changed_signal(self, _tool: CanvasToolName):
        self.toggle_drag_mode()

    def on_canvas_clear_signal(self):
        self.scene.clear()
        self.line_group = QGraphicsItemGroup()
        self.pixmaps = {}
        settings = self.settings
        settings["layers"] = []
        self.settings = settings
        self.emit(SignalCode.LAYER_ADD_SIGNAL)
        self.do_resize_canvas(
            force_draw=True
        )

    def on_load_image_from_path(self, image_path):
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self.load_image_from_object(image)

    def current_image(self):
        image = None
        try:
            layer = self.settings["layers"][self.settings["current_layer_index"]]
            base_64_image = layer["base_64_image"]
            image = Image.open(io.BytesIO(base64.b64decode(base_64_image)))
            image = image.convert("RGBA")
        except IndexError:
            pass
        return image

    def handle_resize_canvas(self):
        self.do_resize_canvas()
    
    def do_resize_canvas(
        self,
        force_draw: bool = False,
        do_draw_layers: bool = None
    ):
        if not self.ui.canvas_container:
            return
        data = {
            'settings': self.settings,
            'view_size': self.ui.canvas_container.viewport().size(),
            'scene': self.scene,
            'line_group': self.line_group,
            'force_draw': force_draw,
            'do_draw_layers': do_draw_layers
        }
        self.emit(SignalCode.CANVAS_RESIZE_SIGNAL, data)

    def window_resized(self, event):
        self.handle_resize_canvas()

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
                        self.set_canvas_color()
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

    def handle_mouse_event(self, original_mouse_event, event):
        if event.buttons() == Qt.MouseButton.MiddleButton:
            if self.last_pos:
                delta = event.pos() - self.last_pos
                horizontal_value = self.ui.canvas_container.horizontalScrollBar().value()
                vertical_value = self.ui.canvas_container.verticalScrollBar().value()
                horizontal_value -= delta.x()
                vertical_value -= delta.y()
                self.ui.canvas_container.horizontalScrollBar().setValue(horizontal_value)
                self.ui.canvas_container.verticalScrollBar().setValue(vertical_value)
            self.last_pos = event.pos()
            self.do_draw()
        original_mouse_event(event)

    def resizeEvent(self, event):
        if self.ui.canvas_container:
            self.handle_resize_canvas()
        if self.scene:
            self.scene.resize()

    def toggle_drag_mode(self):
        current_tool = self.settings["current_tool"]
        if current_tool is CanvasToolName.SELECTION:
            self.ui.canvas_container.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self.ui.canvas_container.setDragMode(QGraphicsView.DragMode.NoDrag)

    def showEvent(self, event):
        super().showEvent(event)
        self.scene = CustomScene(parent=self)

        original_mouse_event = self.ui.canvas_container.mouseMoveEvent
        self.ui.canvas_container.mouseMoveEvent = partial(self.handle_mouse_event, original_mouse_event)
        self.toggle_drag_mode()
        self.ui.canvas_container_size = self.ui.canvas_container.viewport().size()
        self.ui.canvas_container.setContentsMargins(0, 0, 0, 0)
        self.set_canvas_color()
        self.ui.canvas_container.setScene(self.scene)
        self.do_draw(force_draw=True)
    
    def set_canvas_color(self):
        if not self.scene:
            return
        color = QColor(self.settings["grid_settings"]["canvas_color"])
        brush = QBrush(color)
        self.scene.setBackgroundBrush(brush)

    def add_image_to_current_layer(self,value):
        self.logger.info("Adding image to current layer")
        layer_index = self.settings["current_layer_index"]
        base_64_image = ""

        try:
            if value:
                buffered = io.BytesIO()
                value.save(buffered, format="PNG")
                base_64_image = base64.b64encode(buffered.getvalue())
        except Exception as e:
            self.logger.error(e)
        
        settings = self.settings
        # If there's an existing image in the layer, remove it from the scene
        if layer_index in self.pixmaps and isinstance(self.pixmaps[layer_index], QGraphicsItem):
            if self.pixmaps[layer_index].scene() == self.scene:
                self.scene.removeItem(self.pixmaps[layer_index])
            del self.pixmaps[layer_index]
        settings["layers"][layer_index]["base_64_image"] = base_64_image
        self.settings = settings

    def draw_layers(self):
        if not self.do_draw_layers:
            return
        self.do_draw_layers = False
        layers = self.settings["layers"]
        for index, layer in enumerate(layers):
            image = self.get_service(ServiceCode.GET_IMAGE_FROM_LAYER)(layer)
            if image is None:
                continue

            image = apply_opacity_to_image(
                image,
                layer["opacity"] / 100.0
            )

            if not layer["visible"]:
                if (
                    index in self.pixmaps and
                    isinstance(self.pixmaps[index], QGraphicsItem) and
                    self.pixmaps[index].scene() == self.scene
                ):
                    self.scene.removeItem(self.pixmaps[index])
            else:
                # If there's an existing pixmap in the layer, remove it from the scene
                if index in self.pixmaps and isinstance(self.pixmaps[index], QGraphicsItem):
                    if self.pixmaps[index].scene() == self.scene:
                        self.scene.removeItem(self.pixmaps[index])
                    del self.pixmaps[index]
                pixmap = QPixmap()
                pixmap.convertFromImage(ImageQt(image))
                self.pixmaps[index] = DraggablePixmap(pixmap)
                self.emit(SignalCode.LAYER_UPDATE_SIGNAL, {
                    "layer": layer,
                    "index": index
                })
                if self.pixmaps[index].scene() != self.scene:
                    self.scene.addItem(self.pixmaps[index])
            continue

    def set_scene_rect(self):
        self.scene.setSceneRect(
            0,
            0,
            self.ui.canvas_container_size.width(),
            self.ui.canvas_container_size.height()
        )

    def clear_lines(self):
        self.scene.removeItem(self.line_group)
        self.line_group = QGraphicsItemGroup()

    def draw_active_grid_area_container(self):
        """
        Draw the active grid area container
        """

        # Handle any active selections
        selection_start_pos = self.scene.selection_start_pos
        selection_stop_pos = self.scene.selection_stop_pos

        # This will clear the active grid area while a selection is being made
        if selection_stop_pos is None and selection_start_pos is not None:
            if self.active_grid_area:
                self.scene.removeItem(self.active_grid_area)
                self.active_grid_area = None
            return

        # this will update the active grid area in the settings
        if selection_start_pos is not None and selection_stop_pos is not None:
            rect = QRect(
                selection_start_pos,
                selection_stop_pos
            )

            # update the active grid area in settings
            settings = self.settings
            active_grid_settings = settings["active_grid_settings"]
            active_grid_settings["pos_x"] = rect.x()
            active_grid_settings["pos_y"] = rect.y()
            active_grid_settings["width"] = rect.width()
            active_grid_settings["height"] = rect.height()
            generator_settings = settings["generator_settings"]
            generator_settings["width"] = rect.width()
            generator_settings["height"] = rect.height()
            settings["active_grid_settings"] = active_grid_settings
            settings["generator_settings"] = generator_settings
            settings["working_width"] = rect.width()
            settings["working_height"] = rect.height()
            self.settings = settings

            # Clear the selection from the scene
            self.scene.clear_selection()

        # Create an ActiveGridArea object if it doesn't exist
        # and add it to the scene
        if not self.active_grid_area:
            self.active_grid_area = ActiveGridArea()
            self.active_grid_area.setZValue(1)
            self.scene.addItem(self.active_grid_area)

    def action_button_clicked_focus(self):
        self.last_pos = QPoint(0, 0)
        self.do_draw()
    
    def do_draw(
        self,
        force_draw: bool = False,
        do_draw_layers: bool = None
    ):
        if do_draw_layers is not None:
            self.do_draw_layers = do_draw_layers
        if (self.drawing or not self.initialized) and not force_draw:
            return
        self.drawing = True
        self.ui.canvas_container_size = self.ui.canvas_container.viewport().size()
        self.set_scene_rect()
        self.draw_layers()
        self.draw_active_grid_area_container()
        self.draw_grid()
        self.ui.canvas_position.setText(
            f"X {-self.settings['canvas_settings']['pos_x']: 05d} Y {self.settings['canvas_settings']['pos_y']: 05d}"
        )
        self.scene.update()
        self.drawing = False
    
    def handle_image_data(self, data):
        options = data["data"]["options"]
        images = data["images"]
        outpaint_box_rect = options["outpaint_box_rect"]
        section = options["generator_section"]
        processed_image, image_root_point, image_pivot_point = self.handle_outpaint(
            outpaint_box_rect,
            images[0],
            section
        )
        self.load_image_from_object(
            processed_image, 
            is_outpaint=section == GeneratorSection.OUTPAINT.value,
            image_root_point=image_root_point
        )
    
    def handle_outpaint(self, outpaint_box_rect, outpainted_image, action=None):
        if self.current_active_image is None:
            point = QPoint(outpaint_box_rect.x(), outpaint_box_rect.y())
            return outpainted_image, QPoint(0, 0), point

        # make a copy of the current canvas image
        existing_image_copy = self.current_active_image.copy()
        width = existing_image_copy.width
        height = existing_image_copy.height

        pivot_point = self.image_pivot_point
        root_point = QPoint(0, 0)
        layer = ServiceLocator.get(ServiceCode.CURRENT_LAYER)
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

        existing_image_pos = [0, 0]
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
        is_outpaint: bool = False,
        image_root_point: QPoint = None
    ):
        self.add_image_to_scene(
            image_data=dict(
                image=image
            ), 
            is_outpaint=is_outpaint, 
            image_root_point=image_root_point
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
            self.scene.removeItem(draggable_pixmap)
            self.emit(SignalCode.LAYER_DELETE_CURRENT_SIGNAL)
            self.update()
    
    def delete_image(self):
        self.logger.info("Deleting image from canvas")
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.scene.removeItem(draggable_pixmap)
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
            self.scene.removeItem(current_draggable_pixmap)
    
    def switch_to_layer(self, layer_index):
        self.emit(SignalCode.LAYER_SWITCH_SIGNAL, layer_index)

    def add_image_to_scene(
        self,
        image_data: dict,
        is_outpaint: bool = False,
        image_root_point: QPoint = None
    ):
        self.do_draw_layers = True
        self.current_active_image = image_data["image"]
        self.do_resize_canvas(
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
        self.current_active_image = self.image_handler.rotate_image(
            angle,
            self.current_active_image
        )
        self.do_resize_canvas(
            force_draw=True,
            do_draw_layers=True
        )

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

    def draw_grid(self):
        self.scene.addItem(self.line_group)

    def cell_size_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()

    def line_width_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()

    def line_color_changed(self, _val):
        self.redraw_lines = True
        self.do_draw()

    def canvas_color_changed(self, _val):
        self.set_canvas_color()
        self.do_draw()