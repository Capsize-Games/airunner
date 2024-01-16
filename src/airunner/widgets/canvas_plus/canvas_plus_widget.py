import io
import math
import subprocess
from functools import partial

from PIL import Image, ImageGrab
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsPixmapItem
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QGraphicsItemGroup

from airunner.aihandler.logger import Logger
from airunner.widgets.canvas_plus.canvas_base_widget import CanvasBaseWidget
from airunner.widgets.canvas_plus.templates.canvas_plus_ui import Ui_canvas
from airunner.utils import apply_opacity_to_image
from airunner.data.session_scope import session_scope
from airunner.widgets.canvas_plus.draggables import DraggablePixmap, ActiveGridArea
from airunner.widgets.canvas_plus.custom_scene import CustomScene


class CanvasPlusWidget(CanvasBaseWidget):
    logger = Logger(prefix="CanvasPlusWidget")
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

    @property
    def image_pivot_point(self):
        try:
            layer = self.app.current_layer()
            return QPoint(layer["pivot_x"], layer["pivot_y"])
        except Exception as e:
            self.logger.error(e)
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        layer = self.app.current_layer()
        self.app.update_current_layer({
            "pivot_x": value.x(),
            "pivot_y": value.y()
        })

    @property
    def brush_size(self):
        return self.app.brush_size

    @property
    def active_grid_area_rect(self):
        settings = self.app.settings
        rect = QRect(
            settings["active_grid_settings"]["pos_x"],
            settings["active_grid_settings"]["pos_y"],
            settings["active_grid_settings"]["width"],
            settings["active_grid_settings"]["height"]
        )

        # apply self.pos_x and self.pox_y to the rect
        rect.translate(self.app.settings["canvas_settings"]["pos_x"], self.app.settings["canvas_settings"]["pos_y"])

        return rect

    @property
    def current_active_image(self):
        return self.app.get_image_from_current_layer()
    
    @current_active_image.setter
    def current_active_image(self, value):
        self.app.add_image_to_current_layer(value)

    @property
    def layer_container_widget(self):
        return self.app.ui.layer_widget
    
    @property
    def canvas_container(self):
        return self.ui.canvas_container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.application_settings_changed_signal.connect(self.handle_changed_signal)
        self.ui.central_widget.resizeEvent = self.resizeEvent
        self.app.add_image_to_canvas_signal.connect(self.handle_add_image_to_canvas)
        self.app.image_data.connect(self.handle_image_data)
        self.app.load_image.connect(self.load_image_from_path)
        self.app.load_image_object.connect(self.add_image_to_scene)
        self.app.loaded.connect(self.handle_loaded)
        self._zoom_level = 1
        self.canvas_container.resizeEvent = self.window_resized
    
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
        return self.app.settings["grid_settings"]["canvas_color"]

    @property
    def line_color(self):
        return self.app.settings["grid_settings"]["line_color"]

    @property
    def line_width(self):
        return self.app.settings["grid_settings"]["line_width"]

    @property
    def cell_size(self):
        return self.app.settings["grid_settings"]["cell_size"]
    
    def current_pixmap(self):
        draggable_pixmap = self.current_draggable_pixmap()
        if draggable_pixmap:
            return draggable_pixmap.pixmap
    
    def current_image(self):
        pixmap = self.current_pixmap()
        if not pixmap:
            return None
        return Image.fromqpixmap(pixmap)

    def window_resized(self, event):
        self.redraw_lines = True
        self.do_draw()

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
        height = self.app.settings["working_height"] + self.cell_size * amount
        if height > 4096:
            height = 4096
        settings = self.app.settings
        settings["working_height"] = height
        self.app.settings = settings
        self.do_draw()
        
    def decrease_active_grid_height(self, amount):
        height = self.app.settings["working_height"] - self.cell_size * amount
        if height < 512:
            height = 512
        settings = self.app.settings
        settings["working_height"] = height
        self.app.settings = settings
        self.do_draw()

    def increase_active_grid_width(self, amount):
        width = self.app.settings["is_maximized"] + self.cell_size * amount
        if width > 4096:
            width = 4096
        settings = self.app.settings
        settings["is_maximized"] = width
        self.app.settings = settings
        self.do_draw()

    def decrease_active_grid_width(self, amount):
        width = self.app.settings["is_maximized"] - self.cell_size * amount
        if width < 512:
            width = 512
        settings = self.app.settings
        settings["is_maximized"] = width
        self.app.settings = settings
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

    def handle_changed_signal(self):
        do_draw = False
        
        grid_settings = self.app.settings["grid_settings"]
        for k,v in grid_settings.items():
            if k not in self.grid_settings or self.grid_settings[k] != v:
                if k == "canvas_color":
                    self.set_canvas_color()
                elif k in ["line_color", "cell_size", "line_width"]:
                    self.redraw_lines = True
                do_draw = True
        
        active_grid_settings = self.app.settings["active_grid_settings"]
        for k,v in active_grid_settings.items():
            if k not in self.grid_settings or self.grid_settings[k] != v:
                if k in ["pos_x", "pos_y", "width", "height"]:
                    self.redraw_lines = True
                do_draw = True
        
        canvas_settings = self.app.settings["canvas_settings"]
        for k,v in canvas_settings.items():
            if k not in self.grid_settings or self.grid_settings[k] != v:
                do_draw = True
        
        if do_draw:
            self.do_draw()

        self.grid_settings = grid_settings
        self.active_grid_settings = active_grid_settings
        self.canvas_settings = canvas_settings
    
    def handle_loaded(self):
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
            self.do_draw()
        if self.scene:
            self.scene.resize()

    def initialize(self):
        # Create a QGraphicsScene object
        self.scene = CustomScene(parent=self)

        self.view = self.canvas_container
        original_mouse_event = self.view.mouseMoveEvent
        self.view.mouseMoveEvent = partial(self.handle_mouse_event, original_mouse_event)
        #self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # # get size from self.app.ui.content_splitter which is a QSplitter
        self.view_size = self.view.viewport().size()

        # # Set the margins of the QGraphicsView object to 0
        self.view.setContentsMargins(0, 0, 0, 0)

        self.set_canvas_color()

        self.view.setScene(self.scene)

        self.do_draw()
    
    def set_canvas_color(self):
        if not self.scene:
            return
        self.scene.setBackgroundBrush(QBrush(QColor(self.canvas_color)))

    def draw_layers(self):
        layers = self.app.settings["layers"]
        for layer in layers:
            image = self.app.get_image_from_layer(layer)
            if image is None:
                continue

            image = apply_opacity_to_image(
                image,
                layer["opacity"] / 100.0
            )

            if not layer["visible"]:
                if layer["pixmap"] in self.scene.items():
                    self.scene.removeItem(layer["pixmap"])
            elif layer["visible"]:
                if type(layer["pixmap"]) is not DraggablePixmap or layer["pixmap"] not in self.scene.items():
                    layer["pixmap"].convertFromImage(ImageQt(image))
                    layer["pixmap"] = DraggablePixmap(self, layer["pixmap"])
                    self.app.update_layer(layer)
                    self.scene.addItem(layer["pixmap"])
            continue

    def set_scene_rect(self):
        self.scene.setSceneRect(0, 0, self.view_size.width(), self.view_size.height())

    def clear_lines(self):
        self.scene.removeItem(self.line_group)
        self.line_group = QGraphicsItemGroup()

    def draw_lines(self):
        width_cells = math.ceil(self.view_size.width() / self.cell_size)
        height_cells = math.ceil(self.view_size.height() / self.cell_size)
        
        pen = QPen(
            QBrush(QColor(self.line_color)),
            self.line_width,
            Qt.PenStyle.SolidLine
        )
        
        # vertical lines
        h = self.view_size.height() + abs(self.app.settings["canvas_settings"]["pos_y"]) % self.cell_size
        y = 0
        for i in range(width_cells):
            x = i * self.cell_size + self.app.settings["canvas_settings"]["pos_x"] % self.cell_size
            line = self.scene.addLine(x, y, x, h, pen)
            self.line_group.addToGroup(line)

        # # horizontal lines
        w = self.view_size.width() + abs(self.app.settings["canvas_settings"]["pos_x"]) % self.cell_size
        x = 0
        for i in range(height_cells):
            y = i * self.cell_size + self.app.settings["canvas_settings"]["pos_y"] % self.cell_size
            line = self.scene.addLine(x, y, w, y, pen)
            self.line_group.addToGroup(line)

        # Add the group to the scene
        self.scene.addItem(self.line_group)

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

    def handle_add_image_to_canvas(self):
        self.draw_layers()

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
        self.draw_active_grid_area_container()
        self.ui.canvas_position.setText(
            f"X {-self.app.settings['canvas_settings']['pos_x']: 05d} Y {self.app.settings['canvas_settings']['pos_y']: 05d}"
        )
        self.scene.update()
        self.drawing = False
    
    def draw_grid(self):
        draw_grid = self.app.settings["grid_settings"]["show_grid"]

        if draw_grid and self.redraw_lines:
            self.clear_lines()
            self.has_lines = False
        self.redraw_lines = False

        if draw_grid and not self.has_lines:
            self.draw_lines()
            self.has_lines = True
        elif not draw_grid and self.has_lines:
            self.clear_lines()
            self.has_lines = False
    
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
        layer = self.app.current_layer()
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
    
    def load_image_from_path(self, image_path):
        print("canvas_plus_widget load_image_from_path", image_path)
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self.load_image_from_object(image)
    
    def load_image_from_object(self, image, is_outpaint=False, image_root_point=None):
        self.add_image_to_scene(image, is_outpaint=is_outpaint, image_root_point=image_root_point)

    def load_image(self, image_path):
        image = Image.open(image_path)
        if self.app.settings["resize_on_paste"]:
            image.thumbnail((self.app.settings["is_maximized"],
                             self.app.settings["working_height"]), Image.ANTIALIAS)
        self.add_image_to_scene(image)
    
    def current_draggable_pixmap(self):
        self.app.current_draggable_pixmap()
        
    def copy_image(self, image:Image=None) -> DraggablePixmap:
        pixmap = self.current_pixmap() if image is None else QPixmap.fromImage(ImageQt(image))
        return self.move_pixmap_to_clipboard(pixmap)

    def cut_image(self):
        self.copy_image()
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.scene.removeItem(draggable_pixmap)
        self.app.delete_current_layer()
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
        if self.app.is_windows:
            return self.image_from_system_clipboard_windows()
        return self.image_from_system_clipboard_linux()

    def move_pixmap_to_clipboard(self, pixmap):
        if self.app.is_windows:
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
        if self.app.settings["resize_on_paste"]:
            image = self.resize_image(image)
        self.add_image_to_scene(image)
    
    def resize_image(self, image):
        image.thumbnail(
            (
                self.app.settings["is_maximized"],
                self.app.settings["working_height"]
            ),
            Image.ANTIALIAS
        )
        return image

    def remove_current_draggable_pixmap_from_scene(self):
        current_draggable_pixmap = self.current_draggable_pixmap()
        if current_draggable_pixmap:
            self.scene.removeItem(current_draggable_pixmap)
    
    def add_layer(self):
        return self.app.ui.layer_widget.add_layer()

    def switch_to_layer(self, layer_index):
        self.app.switch_layer(layer_index)

    def add_image_to_scene(self, image, is_outpaint=False, image_root_point=None):
        #self.image_adder = ImageAdder(self, image, is_outpaint, image_root_point)
        #self.image_adder.finished.connect(self.on_image_adder_finished)
        self.current_active_image = image
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
            # self.app.error_handler(str(e))
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
    
    def update_image_canvas(self):
        print("TODO")

    def rotate_90_clockwise(self):
        if self.current_active_image:
            self.current_active_image = self.current_active_image.transpose(Image.ROTATE_270)
            self.do_draw()

    def rotate_90_counterclockwise(self):
        if self.current_active_image:
            self.current_active_image = self.current_active_image.transpose(Image.ROTATE_90)
            self.do_draw()
