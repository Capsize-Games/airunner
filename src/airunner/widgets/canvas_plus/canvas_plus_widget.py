import io
import math
import subprocess
from functools import partial
import pdb

from PIL import Image, ImageGrab
from PIL.ImageQt import ImageQt, QImage
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QPainter, QCursor
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsPixmapItem, QGraphicsLineItem
from airunner.aihandler.logger import Logger

from airunner.aihandler.settings_manager import SettingsManager
from airunner.cursors.circle_brush import CircleCursor
from airunner.data.db import session
from airunner.data.models import Layer, CanvasSettings, ActiveGridSettings
from airunner.utils import get_session, save_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas_plus.templates.canvas_plus_ui import Ui_canvas


class DraggablePixmap(QGraphicsPixmapItem):
    def __init__(self, parent, pixmap):
        self.parent = parent
        self.settings_manager = SettingsManager()
        super().__init__(pixmap)
        self.pixmap = pixmap
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def snap_to_grid(self):
        grid_size = self.settings_manager.grid_settings.size
        x = round(self.x() / grid_size) * grid_size
        y = round(self.y() / grid_size) * grid_size
        x += self.parent.last_pos.x()
        y += self.parent.last_pos.y()
        self.setPos(x, y)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.snap_to_grid()

    def mouseReleaseEvent(self, event):
        self.snap_to_grid()
        super().mouseReleaseEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawPixmap(self.pixmap.rect(), self.pixmap)


class LayerImageItem(DraggablePixmap):
    def __init__(self, parent, pixmap, layer_image_data):
        self.layer_image_data = layer_image_data
        super().__init__(parent, pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        pos = self.pos()
        self.layer_image_data.pos_x = pos.x()
        self.layer_image_data.pos_y = pos.y()
        save_session()


class ActiveGridArea(DraggablePixmap):
    active_grid_area_color = None
    image = None

    def __init__(self, parent, rect):
        self.settings_manager = SettingsManager()
        self.update_settings()

        super().__init__(parent, self.pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        self.settings_manager.changed_signal.connect(self.handle_changed_signal)

    @property
    def active_grid_area_rect(self):
        return QRect(
            self.settings_manager.active_grid_settings.pos_x,
            self.settings_manager.active_grid_settings.pos_y,
            self.settings_manager.working_width,
            self.settings_manager.working_height
        )

    def update_settings(self):
        border_color = self.settings_manager.generator.active_grid_border_color
        border_color = QColor(border_color)
        border_opacity = self.settings_manager.active_grid_settings.border_opacity
        border_color.setAlpha(border_opacity)
        fill_color = self.get_fill_color()

        self.active_grid_area_color = border_color

        if not self.image:
            self.image = QImage(
                self.active_grid_area_rect.width(),
                self.active_grid_area_rect.height(),
                QImage.Format.Format_ARGB32
            )
        else:
            self.image = self.image.scaled(
                self.active_grid_area_rect.width(),
                self.active_grid_area_rect.height()
            )

        self.image.fill(fill_color)
        self.pixmap = QPixmap.fromImage(self.image)

    def handle_changed_signal(self, key, value):
        if key == "active_grid_settings.fill_opacity":
            self.change_fill_opacity(value)
            self.redraw()
        elif key == "active_grid_settings.border_opacity":
            self.change_border_opacity(value)
            self.redraw()
        elif key == "active_grid_settings.render_border":
            self.toggle_render_border(value)
            self.redraw()
        elif key == "active_grid_settings.render_fill":
            self.toggle_render_fill(value)
            self.redraw()
        elif key == "active_grid_settings.enabled":
            self.redraw()
        elif key == "current_tab":
            self.redraw()
        elif key == "working_width":
            self.redraw()
        elif key == "working_height":
            self.redraw()

    def redraw(self):
        self.update_settings()
        scene = self.scene()
        if scene:
            scene.removeItem(self)
            if self.settings_manager.active_grid_settings.enabled:
                scene.addItem(self)

    def get_fill_color(self):
        fill_color = self.settings_manager.generator.active_grid_fill_color
        fill_color = QColor(fill_color)
        fill_opacity = self.settings_manager.active_grid_settings.fill_opacity
        fill_opacity = max(1, fill_opacity)
        fill_color.setAlpha(fill_opacity)
        return fill_color

    def paint(self, painter: QPainter, option, widget=None):
        if not self.settings_manager.active_grid_settings.render_fill:
            self.pixmap.fill(QColor(0, 0, 0, 1))
        super().paint(painter, option, widget)

        if self.settings_manager.active_grid_settings.render_border:
            size = 4
            painter.setPen(QPen(
                self.active_grid_area_color,
                self.settings_manager.grid_settings.line_width
            ))
            painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
            painter.drawRect(self.active_grid_area_rect)
            painter.setPen(QPen(
                self.active_grid_area_color,
                self.settings_manager.grid_settings.line_width + 1
            ))
            painter.drawRect(QRect(
                self.active_grid_area_rect.x() + size,
                self.active_grid_area_rect.y() + size,
                self.active_grid_area_rect.width() - (size * 2),
                self.active_grid_area_rect.height() - (size * 2)
            ))

    def toggle_render_fill(self, render_fill):
        if not render_fill:
            self.pixmap.fill(QColor(0, 0, 0, 1))
        else:
            self.pixmap.fill(self.get_fill_color())

    def toggle_render_border(self, value):
        pass

    def change_border_opacity(self, value):
        pass

    def change_fill_opacity(self, value):
        self.pixmap.fill(self.get_fill_color())

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        pos = self.pos()
        self.settings_manager.set_value("active_grid_settings.pos_x", pos.x())
        self.settings_manager.set_value("active_grid_settings.pos_y", pos.y())


class CanvasPlusWidget(BaseWidget):
    widget_class_ = Ui_canvas
    scene = None
    view = None
    view_size = None
    cell_size = None
    line_width = None
    line_color = None
    canvas_color = None
    layers = {}
    images = {}
    active_grid_area = None
    active_grid_area_pivot_point = QPoint(0, 0)
    active_grid_area_position = QPoint(0, 0)
    last_pos = QPoint(0, 0)
    current_image_index = 0
    draggable_pixmaps_in_scene = {}

    @property
    def image_pivot_point(self):
        try:
            return QPoint(self.current_layer.pivot_x, self.current_layer.pivot_y)
        except Exception as e:
            print(e)
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        self.current_layer.pivot_x = value.x()
        self.current_layer.pivot_y = value.y()
        save_session()

    @property
    def active_grid_area_selected(self):
        return self.settings_manager.current_tool == "active_grid_area"

    @property
    def select_selected(self):
        return self.settings_manager.current_tool == "select"

    @property
    def eraser_selected(self):
        return self.settings_manager.current_tool == "eraser"

    @property
    def brush_selected(self):
        return self.settings_manager.current_tool == "brush"

    @property
    def move_selected(self):
        return self.settings_manager.current_tool == "move"

    @property
    def brush_size(self):
        return self.settings_manager.brush_settings.size

    @property
    def active_grid_area_rect(self):
        rect = QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.active_grid_settings.width,
            self.active_grid_settings.height
        )

        # apply self.pos_x and self.pox_y to the rect
        rect.translate(self.canvas_settings.pos_x, self.canvas_settings.pos_y)

        return rect

    @property
    def current_active_image(self):
        return self.current_layer.image
    
    @current_active_image.setter
    def current_active_image(self, value):
        self.current_layer.image = value

    @property
    def current_layer(self):
        return self.layer_container_widget.current_layer

    @property
    def current_layer_index(self):
        return self.layer_container_widget.current_layer_index
    
    @current_layer_index.setter
    def current_layer_index(self, value):
        self.layer_container_widget.current_layer_index = value

    @property
    def layer_container_widget(self):
        return self.app.ui.layer_widget
    
    initialized = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.canvas_settings = session.query(CanvasSettings).first()
        self.active_grid_settings = session.query(ActiveGridSettings).first()
        self.ui.central_widget.resizeEvent = self.resizeEvent
        self.app.add_image_to_canvas_signal.connect(self.handle_add_image_to_canvas)
        self.app.image_data.connect(self.handle_image_data)
        self.app.load_image.connect(self.load_image_from_path)
        self.layer_data = session.query(
            Layer
        ).filter(
            Layer.document_id == self.app.document.id,
        ).order_by(
            Layer.position.asc()
        ).all()
        self.initialize()
        #self.settings_manager.changed_signal.connect(self.handle_changed_signal)
        self.app.loaded.connect(self.handle_loaded)
    
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

    def initialize(self):
        # Create a QGraphicsScene object
        self.scene = QGraphicsScene()

        self.view = self.ui.canvas_container
        original_mouse_event = self.view.mouseMoveEvent
        self.view.mouseMoveEvent = partial(self.handle_mouse_event, original_mouse_event)
        #self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # # get size from self.app.ui.content_splitter which is a QSplitter
        self.view_size = self.view.viewport().size()

        # # initialize variables
        self.cell_size = self.settings_manager.grid_settings.size
        self.line_width = self.settings_manager.grid_settings.line_width
        self.line_color = QColor(self.settings_manager.grid_settings.line_color)
        self.canvas_color = QColor(self.settings_manager.grid_settings.canvas_color)

        # # Set the margins of the QGraphicsView object to 0
        self.view.setContentsMargins(0, 0, 0, 0)

        self.scene.setBackgroundBrush(QBrush(self.canvas_color))
        self.view.setScene(self.scene)

        self.do_draw()

    def draw_layers(self):
        for layer in self.layer_data:
            image = layer.image
            if image is None:
                continue

            draggable_pixmap = None
            if layer.id in self.layers:
                self.layers[layer.id].pixmap.convertFromImage(ImageQt(image))
                draggable_pixmap = self.layers[layer.id]
                self.scene.removeItem(draggable_pixmap)
            
            if not draggable_pixmap:
                draggable_pixmap = DraggablePixmap(self, QPixmap.fromImage(ImageQt(image)))
                self.layers[layer.id] = draggable_pixmap

            print("ADDING ITEM TO SCENE")
            if layer.visible:
                print("adding")
                self.scene.addItem(draggable_pixmap)
            print("creating point")
            pos = QPoint(layer.pos_x, layer.pos_y)
            print("setting pos")
            draggable_pixmap.setPos(QPointF(
                self.canvas_settings.pos_x + pos.x(),
                self.canvas_settings.pos_y + pos.y()
            ))

    def handle_changed_signal(self, key, value):
        if key == "current_tab":
            self.do_draw()
        elif key == "current_section_stablediffusion":
            self.do_draw()
        elif key == "current_section_kandinsky":
            self.do_draw()
        elif key == "current_section_shapegif":
            self.do_draw()
        elif key == "layer_image_data.visible":
            self.do_draw()
        elif key == "layer_data.hidden":
            self.do_draw()
        elif key == "active_image_editor_section":
            self.do_draw()
        elif key == "grid_settings.show_grid":
            # remove lines from scene
            for item in self.scene.items():
                if isinstance(item, QGraphicsLineItem):
                    self.scene.removeItem(item)
            self.do_draw()

    def set_scene_rect(self):
        self.scene.setSceneRect(0, 0, self.view_size.width(), self.view_size.height())

    def draw_lines(self):
        width_cells = math.ceil(self.view_size.width() / self.cell_size)
        height_cells = math.ceil(self.view_size.height() / self.cell_size)

        pen = QPen(
            QBrush(self.line_color),
            self.line_width,
            Qt.PenStyle.SolidLine
        )

        if self.settings_manager.grid_settings.show_grid:
            # vertical lines
            h = self.view_size.height() + abs(self.canvas_settings.pos_y) % self.cell_size
            y = 0
            for i in range(width_cells):
                x = i * self.cell_size + self.canvas_settings.pos_x % self.cell_size
                self.scene.addLine(x, y, x, h, pen)

            # # horizontal lines
            w = self.view_size.width() + abs(self.canvas_settings.pos_x) % self.cell_size
            x = 0
            for i in range(height_cells):
                y = i * self.cell_size + self.canvas_settings.pos_y % self.cell_size
                self.scene.addLine(x, y, w, y, pen)

    def draw_active_grid_area_container(self):
        """
        Draw a rectangle around the active grid area of
        """
        # if not self.active_grid_area:
        #     self.active_grid_area = ActiveGridArea(
        #         parent=self,
        #         rect=self.active_grid_area_rect
        #     )
        #     self.active_grid_area.setZValue(1)
        #     self.scene.addItem(self.active_grid_area)
        # else:
        #     self.active_grid_area.redraw()
        pass

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
        self.draw_lines()
        self.draw_layers()
        #self.draw_active_grid_area_container()
        print("setting canvas position text")
        self.ui.canvas_position.setText(
            f"X {-self.canvas_settings.pos_x: 05d} Y {self.canvas_settings.pos_y: 05d}"
        )
        self.scene.update()
        self.drawing = False
    
    drawing = False


    def update_cursor(self):
        # if self.is_canvas_drag_mode:
        #     # show as grab cursor
        #     self.canvas_container.setCursor(Qt.CursorShape.ClosedHandCursor)
        if self.move_selected:
            self.ui.canvas_container.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self.active_grid_area_selected:
            self.ui.canvas_container.setCursor(Qt.CursorShape.DragMoveCursor)
        elif self.brush_selected or self.eraser_selected:
            self.ui.canvas_container.setCursor(
                CircleCursor(
                    Qt.GlobalColor.white,
                    Qt.GlobalColor.transparent,
                    self.brush_size
                )
            )
        else:
            self.ui.canvas_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def handle_image_data(self, data):
        self.load_image_from_object(data["images"][0])
    
    def load_image_from_path(self, image_path):
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self.load_image_from_object(image)
    
    def load_image_from_object(self, image):
        if self.app.image_editor_tab_name == "Canvas":
            self.add_image_to_scene(image)

    def load_image(self, image_path):
        image = Image.open(image_path)
        if self.app.settings_manager.resize_on_paste:
            image.thumbnail((self.settings_manager.working_width,
                             self.settings_manager.working_height), Image.ANTIALIAS)
        self.add_image_to_scene(image)
    
    def current_draggable_pixmap(self):
        if self.current_layer_index in self.draggable_pixmaps_in_scene:
            return self.draggable_pixmaps_in_scene[self.current_layer_index]

    def current_pixmap(self):
        draggable_pixmap = self.current_draggable_pixmap()
        if draggable_pixmap:
            return draggable_pixmap.pixmap

    def copy_image(self) -> DraggablePixmap:
        return self.move_pixmap_to_clipboard(self.current_pixmap())

    def cut_image(self):
        self.copy_image()
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.scene.removeItem(draggable_pixmap)
        self.update()
    
    def delete_image(self):
        Logger.info("Deleting image from canvas")
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.scene.removeItem(draggable_pixmap)
        self.update()
    
    def paste_image_from_clipboard(self):
        image = self.get_image_from_clipboard()

        if not image:
            Logger.info("No image in clipboard")
            return

        if self.app.settings_manager.resize_on_paste:
            Logger.info("Resizing image")
            image.thumbnail(
                (self.settings_manager.working_width, self.settings_manager.working_height), 
                Image.ANTIALIAS)
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
            pass

    def create_image(self, image):
        if self.app.settings_manager.resize_on_paste:
            image.thumbnail(
                (
                    self.settings_manager.working_width,
                    self.settings_manager.working_height
                ),
                Image.ANTIALIAS
            )
        self.add_image_to_scene(image)
    
    def save_image_to_database(self, image):
        self.current_active_image = image
        session.add(self.current_layer)
        save_session()
    
    def remove_current_draggable_pixmap_from_scene(self):
        current_draggable_pixmap = self.current_draggable_pixmap()
        if current_draggable_pixmap:
            self.scene.removeItem(current_draggable_pixmap)
    
    def add_layer(self):
        return self.app.ui.layer_widget.add_layer()

    def switch_to_layer(self, layer_index):
        self.current_layer_index = layer_index

    def add_image_to_scene(self, image):
        print("saving image to database")
        self.save_image_to_database(image)
        print("calling do_draw")
        self.do_draw()
        print("image added to scene")
    
    def image_to_system_clipboard_windows(self, pixmap):
        if not pixmap:
            return None
        Logger.info("image_to_system_clipboard_windows")
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
        Logger.info("image_from_system_clipboard_windows")
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
        Logger.info("image_from_system_clipboard_linux")
        try:
            image = ImageGrab.grabclipboard()
            if not image:
                Logger.info("No image in clipboard")
                return None
            # with transparency
            image = image.convert("RGBA")
            return image
        except Exception as e:
            print(e)
            return None

    def save_image(self, image_path):
        # 1. iterate over all images in self.sce
        for item in self.scene.items():
            if isinstance(item, QGraphicsPixmapItem):
                image = item.pixmap.toImage()
                image.save(image_path)

    def filter_with_filter(self, filter):
        return type(filter).__name__ in [
            "SaturationFilter", 
            "ColorBalanceFilter", 
            "RGBNoiseFilter", 
            "PixelFilter", 
            "HalftoneFilter", 
            "RegistrationErrorFilter"]


    @property
    def current_active_image_data(self):
        return self.current_layer.image_data
    
    @current_active_image_data.setter
    def current_active_image_data(self, value):
        self.current_layer.image_data = value

    def preview_filter(self, filter):
        if len(self.current_active_image_data) == 0:
            return
        for image_data in self.current_active_image_data:
            image = image_data.image
            if self.filter_with_filter:
                filtered_image = filter.filter(image)
            else:
                filtered_image = image.filter(filter)
            image_data.image = filtered_image
    
    def cancel_filter(self):
        for index in range(len(self.current_active_image_data)):
            self.current_active_image_data[index] = self.image_data[index]
        self.image_data = []
    
    def apply_filter(self, filter):
        for image_data, index in iter(self.current_layer):
            if image_data.image is None:
                continue
            self.app.history.add_event({
                "event": "apply_filter",
                "layer_index": self.current_layer_index,
                "images": image_data,
            })

            if self.filter_with_filter:
                filtered_image = filter.filter(self.image_data[index].image)
            else:
                filtered_image = self.image_data[index].image.filter(filter)
            self.current_active_image = filtered_image
            self.image_data = []
    
    def update_image_canvas(self):
        print("TODO")
