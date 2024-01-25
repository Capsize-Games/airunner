import io
import base64
import subprocess
from functools import partial

from PIL import Image, ImageGrab
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QBrush, QColor, QPixmap
from PyQt6.QtWidgets import QGraphicsPixmapItem
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QGraphicsItemGroup, QGraphicsItem

from airunner.enums import SignalCode, ServiceCode
from airunner.workers.canvas_resize_worker import CanvasResizeWorker
from airunner.workers.image_data_worker import ImageDataWorker
from airunner.widgets.canvas_plus.templates.canvas_plus_ui import Ui_canvas
from airunner.utils import apply_opacity_to_image
from airunner.widgets.canvas_plus.draggables import DraggablePixmap, ActiveGridArea
from airunner.widgets.canvas_plus.custom_scene import CustomScene
from airunner.widgets.base_widget import BaseWidget
from airunner.service_locator import ServiceLocator


class CanvasPlusWidget(BaseWidget):
    widget_class_ = Ui_canvas
    scene = None
    view = None
    view_size = None
    layers = {}
    images = {}
    active_grid_area = None
    active_grid_area_pivot_point = QPoint(0, 0)
    active_grid_area_position = QPoint(0, 0)
    last_pos = QPoint(0, 0)
    current_image_index = 0
    draggable_pixmaps_in_scene = {}
    initialized = False
    drawing = False
    redraw_lines = False
    has_lines = False
    line_group = QGraphicsItemGroup()
    grid_settings: dict = {}
    active_grid_settings: dict = {}
    canvas_settings: dict = {}
    image = None
    image_backup = None
    previewing_filter = False
    drag_pos: QPoint = None

    @property
    def image_pivot_point(self):
        try:
            layer = ServiceLocator.get(ServiceCode.CURRENT_LAYER)
            return QPoint(layer["pivot_point_x"], layer["pivot_point_y"])
        except Exception as e:
            self.logger.error(e)
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        self.emit(SignalCode.UPDATE_CURRENT_LAYER_SIGNAL, dict(
            pivot_point_x=value.x(),
            pivot_point_y=value.y()
        ))

    @property
    def brush_size(self):
        return self.settings["brush_settings"]["size"]

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
    
    @property
    def layer_container_widget(self):
        # TODO
        return ServiceLocator(ServiceCode.LAYER_WIDGET)
    
    @property
    def canvas_container(self):
        return self.ui.canvas_container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.central_widget.resizeEvent = self.resizeEvent
        self.register(SignalCode.MAIN_WINDOW_LOADED_SIGNAL, self.on_main_window_loaded_signal)
        self._zoom_level = 1
        self.canvas_container.resizeEvent = self.window_resized
        self.pixmaps = {}

        self.image_data_worker = self.create_worker(ImageDataWorker)
        self.canvas_resize_worker = self.create_worker(CanvasResizeWorker)
        self.register(SignalCode.CANVAS_DO_DRAW_SIGNAL, self.on_canvas_do_draw_signal)
        self.register(SignalCode.CANVAS_CLEAR_LINES_SIGNAL, self.on_canvas_clear_lines_signal)
        self.register(SignalCode.IMAGE_DATA_WORKER_RESPONSE_SIGNAL, self.on_ImageDataWorker_response_signal)
        self.register(SignalCode.CANVAS_RESIZE_WORKER_RESPONSE_SIGNAL, self.on_CanvasResizeWorker_response_signal)
        self.register(SignalCode.IMAGE_GENERATED_SIGNAL, self.on_image_generated_signal)
        self.register(SignalCode.LOAD_IMAGE_FROM_PATH_SIGNAL, self.on_load_image_from_path)
        self.register(SignalCode.CANVAS_HANDLE_LAYER_CLICK_SIGNAL, self.on_canvas_handle_layer_click_signal)
        self.register(SignalCode.UPDATE_CANVAS_SIGNAL, self.on_update_canvas_signal)
        self.register(SignalCode.SET_CURRENT_LAYER_SIGNAL, self.on_set_current_layer_signal)
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)

        self.register_service("canvas_drag_pos", self.canvas_drag_pos)
        self.register_service("canvas_current_active_image", self.canvas_current_active_image)
    
    def on_set_current_layer_signal(self, args):
        self.set_current_layer(args)
        
    def set_current_layer(self, args):
        index, current_layer_index = args
        item = self.ui.container.layout().itemAt(current_layer_index)
        if item:
            item.widget().frame.setStyleSheet(self.css("layer_normal_style"))
        if self.ui.container:
            item = self.ui.container.layout().itemAt(index)
            if item:
                item.widget().frame.setStyleSheet(self.css("layer_highlight_style"))

    def on_update_canvas_signal(self, _ignore):
        self.update()
    
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

    def on_canvas_do_draw_signal(self):
        self.do_draw()

    def on_image_generated_signal(self, image_data: dict):
        # self.image_data_worker.add_to_queue(dict(
        #     auto_export_images=self.settings["auto_export_images"],
        #     base_path=self.settings["path_settings"]["base_path"],
        #     image_path=self.settings["path_settings"]["image_path"],
        #     image_export_type=self.settings["image_export_type"],
        #     image_data=image_data
        # ))
        self.add_image_to_scene(image_data["images"][0])

    def on_CanvasResizeWorker_response_signal(self, lines_data: list):
        draw_grid = self.settings["grid_settings"]["show_grid"]
        if not draw_grid:
            return
        for line_data in lines_data:
            try:
                line = self.scene.addLine(*line_data)
                self.line_group.addToGroup(line)
            except TypeError as e:
                self.logger.error(f"TypeError: {e}")

    def on_ImageDataWorker_response_signal(self, message):
        self.emit(SignalCode.CLEAR_STATUS_MESSAGE_SIGNAL)
        self.emit(SignalCode.STOP_IMAGE_GENERATOR_PROGRESS_BAR_SIGNAL)
        nsfw_content_detected = message["nsfw_content_detected"]
        path = message["path"]
        if nsfw_content_detected and self.parent.settings["nsfw_filter"]:
            self.emit(SignalCode.ERROR_SIGNAL, "Explicit content detected, try again.")
        self.emit(SignalCode.SHOW_LAYERS_SIGNAL)
        if path is not None:
            self.emit(SignalCode.SET_STATUS_LABEL_SIGNAL, f"Image generated to {path}")
    
    @property
    def zoom_in_step(self):
        if self.zoom_level > 6:
            return 2
        elif self.zoom_level > 4:
            return 1
        return 0.1

    @property
    def zoom_out_step(self):
        if self.zoom_level > 6:
            return 2
        elif self.zoom_level > 4:
            return 1
        if self.zoom_level <= 1.0:
            return 0.05
        return 0.1
    
    @property
    def zoom_level(self):
        zoom = self._zoom_level
        if zoom <= 0:
            zoom = 0.1
        return zoom

    @zoom_level.setter
    def zoom_level(self, value):
        self._zoom_level = value
    
    @property
    def canvas_color(self):
        return self.settings["grid_settings"]["canvas_color"]

    @property
    def line_color(self):
        return self.settings["grid_settings"]["line_color"]

    @property
    def line_width(self):
        return self.settings["grid_settings"]["line_width"]

    @property
    def cell_size(self):
        return self.settings["grid_settings"]["cell_size"]
    
    def current_pixmap(self):
        draggable_pixmap = self.current_draggable_pixmap()
        if draggable_pixmap:
            return draggable_pixmap.pixmap
    
    def current_image(self):
        pixmap = self.current_pixmap()
        if not pixmap:
            return None
        return Image.fromqpixmap(pixmap)

    def handle_resize_canvas(self):
        self.do_resize_canvas()
    
    def do_resize_canvas(self):
        if not self.view:
            return
        data = dict(
            settings=self.settings,
            view_size=self.view.viewport().size(),
            scene=self.scene,
            line_group=self.line_group
        )
        self.emit(SignalCode.CANVAS_RESIZE_SIGNAL, data)

    def window_resized(self, event):
        self.handle_resize_canvas()

    def toggle_grid(self, val):
        self.do_draw()
    
    def cell_size_changed(self, val):
        self.redraw_lines = True
        self.do_draw()
    
    def line_width_changed(self, val):
        self.redraw_lines = True
        self.do_draw()
    
    def line_color_changed(self, val):
        self.redraw_lines = True
        self.do_draw()

    def canvas_color_changed(self, val):
        self.set_canvas_color()
        self.do_draw()

    def increase_active_grid_height(self, amount):
        height = self.settings["working_height"] + self.cell_size * amount
        if height > 4096:
            height = 4096
        settings = self.settings
        settings["working_height"] = height
        self.settings = settings
        self.do_draw()
        
    def decrease_active_grid_height(self, amount):
        height = self.settings["working_height"] - self.cell_size * amount
        if height < 512:
            height = 512
        settings = self.settings
        settings["working_height"] = height
        self.settings = settings
        self.do_draw()

    def increase_active_grid_width(self, amount):
        width = self.settings["is_maximized"] + self.cell_size * amount
        if width > 4096:
            width = 4096
        settings = self.settings
        settings["is_maximized"] = width
        self.settings = settings
        self.do_draw()

    def decrease_active_grid_width(self, amount):
        width = self.settings["is_maximized"] - self.cell_size * amount
        if width < 512:
            width = 512
        settings = self.settings
        settings["is_maximized"] = width
        self.settings = settings
        self.do_draw()

    def wheelEvent(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.increase_active_grid_height(int(abs(event.angleDelta().y()) / 120))
            else:
                self.decrease_active_grid_height(int(abs(event.angleDelta().y()) / 120))
        elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
            if event.angleDelta().y() > 0:
                self.increase_active_grid_width(int(abs(event.angleDelta().y()) / 120))
            else:
                self.decrease_active_grid_width(int(abs(event.angleDelta().y()) / 120))
        elif modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier:
            if event.angleDelta().y() > 0:
                self.increase_active_grid_height(int(abs(event.angleDelta().y()) / 120))
                self.increase_active_grid_width(int(abs(event.angleDelta().y()) / 120))
            else:
                self.decrease_active_grid_height(int(abs(event.angleDelta().y()) / 120))
                self.decrease_active_grid_width(int(abs(event.angleDelta().y()) / 120))
        else:
            super().wheelEvent(event)  # Propagate the event to the base class if no modifier keys are pressed

    def on_application_settings_changed_signal(self):
        do_draw = False

        self.do_resize_canvas()
        
        grid_settings = self.settings["grid_settings"]
        for k,v in grid_settings.items():
            if k not in grid_settings or grid_settings[k] != v:
                if k == "canvas_color":
                    self.set_canvas_color()
                elif k in ["line_color", "cell_size", "line_width"]:
                    self.redraw_lines = True
                do_draw = True
        
        active_grid_settings = self.settings["active_grid_settings"]
        for k,v in active_grid_settings.items():
            if k not in self.active_grid_settings or self.active_grid_settings[k] != v:
                if k in ["pos_x", "pos_y", "width", "height"]:
                    self.redraw_lines = True
                do_draw = True
        
        canvas_settings = self.settings["canvas_settings"]
        for k,v in canvas_settings.items():
            if k not in self.canvas_settings or self.canvas_settings[k] != v:
                self.logger.debug("canvas_settings changed")
                do_draw = True
        
        if do_draw:
            self.do_draw()

        settings = self.settings
        settings["grid_settings"] = grid_settings
        self.active_grid_settings = active_grid_settings
        self.canvas_settings = canvas_settings
        self.settings = settings
    
    def on_main_window_loaded_signal(self):
        self.initialized = True

    def handle_mouse_event(self, original_mouse_event, event):
        if event.buttons() == Qt.MouseButton.MiddleButton:
            if self.last_pos:
                delta = event.pos() - self.last_pos
                self.view.horizontalScrollBar().setValue(self.view.horizontalScrollBar().value() - delta.x())
                self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().value() - delta.y())
            self.last_pos = event.pos()
            self.do_draw()
        original_mouse_event(event)

    def resizeEvent(self, event):
        if self.view:
            self.handle_resize_canvas()
        if self.scene:
            self.scene.resize()

    def showEvent(self, event):
        super().showEvent(event)
        self.scene = CustomScene(parent=self)

        self.view = self.canvas_container
        original_mouse_event = self.view.mouseMoveEvent
        self.view.mouseMoveEvent = partial(self.handle_mouse_event, original_mouse_event)
        #self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        self.view_size = self.view.viewport().size()
        self.view.setContentsMargins(0, 0, 0, 0)
        self.set_canvas_color()
        self.view.setScene(self.scene)
        self.do_draw()
    
    def set_canvas_color(self):
        if not self.scene:
            return
        self.scene.setBackgroundBrush(QBrush(QColor(self.canvas_color)))

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
                if index in self.pixmaps and isinstance(self.pixmaps[index], QGraphicsItem) and self.pixmaps[index].scene() == self.scene:
                    self.scene.removeItem(self.pixmaps[index])
            elif layer["visible"]:
                # If there's an existing pixmap in the layer, remove it from the scene
                if index in self.pixmaps and isinstance(self.pixmaps[index], QGraphicsItem):
                    if self.pixmaps[index].scene() == self.scene:
                        self.scene.removeItem(self.pixmaps[index])
                    del self.pixmaps[index]
                pixmap = QPixmap()
                pixmap.convertFromImage(ImageQt(image))
                self.pixmaps[index] = DraggablePixmap(self, pixmap)
                self.emit(SignalCode.UPDATE_LAYER_SIGNAL, dict(
                    layer=layer,
                    index=index
                ))
                if self.pixmaps[index].scene() != self.scene:
                    self.scene.addItem(self.pixmaps[index])
            continue

    def set_scene_rect(self):
        self.scene.setSceneRect(0, 0, self.view_size.width(), self.view_size.height())

    def clear_lines(self):
        self.scene.removeItem(self.line_group)
        self.line_group = QGraphicsItemGroup()

    def draw_active_grid_area_container(self):
        """
        Draw a rectangle around the active grid area of
        """
        if not self.active_grid_area:
            self.active_grid_area = ActiveGridArea(
                parent=self,
                rect=self.active_grid_area_rect
            )
            self.active_grid_area.setZValue(1)
            self.scene.addItem(self.active_grid_area)
        else:
            self.active_grid_area.redraw()

    def action_button_clicked_focus(self):
        self.last_pos = QPoint(0, 0)
        self.do_draw()
    
    def do_draw(self):
        if self.drawing or not self.initialized:
            return
        self.drawing = True
        self.view_size = self.view.viewport().size()
        self.set_scene_rect()
        self.draw_grid()
        self.draw_layers()
        #self.draw_active_grid_area_container()
        self.ui.canvas_position.setText(
            f"X {-self.settings['canvas_settings']['pos_x']: 05d} Y {self.settings['canvas_settings']['pos_y']: 05d}"
        )
        self.scene.update()
        self.drawing = False
    
    def draw_grid(self):
        self.scene.addItem(self.line_group)
    
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
            is_outpaint=section == "outpaint",
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

        if action == "outpaint":
            new_image = Image.alpha_composite(new_image, new_image_a)
            new_image = Image.alpha_composite(new_image, new_image_b)
        else:
            new_image = Image.alpha_composite(new_image, new_image_b)
            new_image = Image.alpha_composite(new_image, new_image_a)

        return new_image, image_root_point, image_pivot_point
    
    def on_load_image_from_path(self, image_path):
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self.load_image_from_object(image)
    
    def load_image_from_object(self, image, is_outpaint=False, image_root_point=None):
        self.add_image_to_scene(
            image_data=dict(
                image=image
            ), 
            is_outpaint=is_outpaint, 
            image_root_point=image_root_point
        )

    def load_image(self, image_path):
        image = Image.open(image_path)
        if self.settings["resize_on_paste"]:
            image.thumbnail((self.settings["is_maximized"],
                             self.settings["working_height"]), Image.ANTIALIAS)
        self.add_image_to_scene(image)
    
    def current_draggable_pixmap(self):
        return ServiceLocator.get(ServiceCode.CURRENT_DRAGGABLE_PIXMAP)
        
    def copy_image(self, image:Image=None) -> DraggablePixmap:
        pixmap = self.current_pixmap() if image is None else QPixmap.fromImage(ImageQt(image))
        return self.move_pixmap_to_clipboard(pixmap)

    def cut_image(self):
        self.copy_image()
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.scene.removeItem(draggable_pixmap)
        self.emit(SignalCode.DELETE_CURRENT_LAYER_SIGNAL)
        self.update()
    
    def delete_image(self):
        self.logger.info("Deleting image from canvas")
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.scene.removeItem(draggable_pixmap)
        self.update()
    
    def paste_image_from_clipboard(self):
        self.logger.info("paste image from clipboard")
        image = self.get_image_from_clipboard()

        if not image:
            self.logger.info("No image in clipboard")
            return

        self.create_image(image)
    
    def get_image_from_clipboard(self):
        if self.is_windows:
            return self.image_from_system_clipboard_windows()
        return self.image_from_system_clipboard_linux()

    def move_pixmap_to_clipboard(self, pixmap):
        if self.is_windows:
            return self.image_to_system_clipboard_windows(pixmap)
        return self.image_to_system_clipboard_linux(pixmap)
    
    def image_to_system_clipboard_linux(self, pixmap):
        if not pixmap:
            return None
        data = io.BytesIO()
        
        # Convert QImage to PIL Image
        image = Image.fromqpixmap(pixmap)
        
        # Save PIL Image to BytesIO
        image.save(data, format="png")
        
        data = data.getvalue()
        try:
            subprocess.Popen(["xclip", "-selection", "clipboard", "-t", "image/png"],
                            stdin=subprocess.PIPE).communicate(data)
        except FileNotFoundError:
            self.logger.error("xclip not found. Please install xclip to copy image to clipboard.")

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
    
    def add_layer(self):
        self.emit(SignalCode.ADD_LAYER_SIGNAL)

    def switch_to_layer(self, layer_index):
        self.emit(SignalCode.SWITCH_LAYER_SIGNAL, layer_index)

    def add_image_to_scene(self, image_data, is_outpaint=False, image_root_point=None):
        #self.image_adder = ImageAdder(self, image, is_outpaint, image_root_point)
        #self.image_adder.finished.connect(self.on_image_adder_finished)
        self.current_active_image = image_data["image"]
        self.do_draw()
        #self.image_adder.start()
    
    def image_to_system_clipboard_windows(self, pixmap):
        if not pixmap:
            return None
        self.logger.info("image_to_system_clipboard_windows")
        import win32clipboard
        data = io.BytesIO()
        # Convert QImage to PIL Image
        image = Image.fromqpixmap(pixmap)
        # Save PIL Image to BytesIO
        image.save(data, format="png")
        data = data.getvalue()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def image_from_system_clipboard_windows(self):
        self.logger.info("image_from_system_clipboard_windows")
        import win32clipboard
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            win32clipboard.CloseClipboard()
            # convert bytes to image
            image = Image.open(io.BytesIO(data))
            return image
        except Exception as e:
            print(e)
            return None
    
    def image_from_system_clipboard_linux(self):
        self.logger.info("image_from_system_clipboard_linux")
        try:
            image = ImageGrab.grabclipboard()
            if not image:
                self.logger.info("No image in clipboard")
                return None
            # with transparency
            image = image.convert("RGBA")
            return image
        except Exception as e:
            print(e)
            return None

    def save_image(self, image_path, image=None):
        # 1. iterate over all images in self.sce
        if image is None:
            for item in self.scene.items():
                if isinstance(item, QGraphicsPixmapItem):
                    image = item.pixmap.toImage()
                    image.save(image_path)
        else:
            image.save(image_path)

    def rotate_90_clockwise(self):
        if self.current_active_image:
            self.current_active_image = self.current_active_image.transpose(Image.ROTATE_270)
            self.do_draw()

    def rotate_90_counterclockwise(self):
        if self.current_active_image:
            self.current_active_image = self.current_active_image.transpose(Image.ROTATE_90)
            self.do_draw()

    def current_image(self):
        if self.previewing_filter:
            return self.image_backup.copy()
        return self.image
    
    def filter_with_filter(self, filter):
        return type(filter).__name__ in [
            "SaturationFilter", 
            "ColorBalanceFilter", 
            "RGBNoiseFilter", 
            "PixelFilter", 
            "HalftoneFilter", 
            "RegistrationErrorFilter"]

    def preview_filter(self, filter):
        image = self.current_image()
        if not image:
            return
        if not self.previewing_filter:
            self.image_backup = image.copy()
            self.previewing_filter = True
        else:
            image = self.image_backup.copy()
        if self.filter_with_filter:
            filtered_image = filter.filter(image)
        else:
            filtered_image = image.filter(filter)
        self.load_image_from_object(image=filtered_image)
    
    def cancel_filter(self):
        if self.image_backup:
            self.load_image_from_object(image=self.image_backup)
            self.image_backup = None
        self.previewing_filter = False
    
    def apply_filter(self, filter):
        self.previewing_filter = False
        self.image_backup = None