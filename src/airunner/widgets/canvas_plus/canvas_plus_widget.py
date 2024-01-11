import io
import math
import subprocess
from functools import partial

from PIL import Image, ImageGrab
from PIL.ImageQt import ImageQt, QImage
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QPainter, QCursor
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsPixmapItem, QGraphicsLineItem
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtCore import QLineF

from airunner.aihandler.logger import Logger
from airunner.cursors.circle_brush import CircleCursor
from airunner.data.models import Layer, CanvasSettings
from airunner.widgets.canvas_plus.canvas_base_widget import CanvasBaseWidget
from airunner.widgets.canvas_plus.templates.canvas_plus_ui import Ui_canvas
from airunner.utils import apply_opacity_to_image
from airunner.data.session_scope import session_scope
from airunner.data.managers import SettingsManager


class ImageAdder(QThread):
    finished = pyqtSignal()

    def __init__(self, widget, image, is_outpaint, image_root_point):
        super().__init__()
        self.widget = widget
        self.image = image
        self.is_outpaint = is_outpaint
        self.image_root_point = image_root_point

    def run(self):
        with session_scope() as session:
            self.widget.current_active_image = self.image
            if self.image_root_point is not None:
                self.widget.current_layer.pos_x = self.image_root_point.x()
                self.widget.current_layer.pos_y = self.image_root_point.y()
            elif not self.is_outpaint:
                self.widget.current_layer.pos_x = self.widget.active_grid_area_rect.x()
                self.widget.current_layer.pos_y = self.widget.active_grid_area_rect.y()
            session.add(self.widget.current_layer)
            self.widget.do_draw()
            self.finished.emit()


class DraggablePixmap(QGraphicsPixmapItem):
    def __init__(self, parent, pixmap):
        self.parent = parent
        super().__init__(pixmap)
        self.pixmap = pixmap
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)


    def snap_to_grid(self):
        grid_size = self.parent.settings_manager.grid_settings.cell_size
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
        with session_scope() as session:
            pos = self.pos()
            self.layer_image_data.pos_x = pos.x()
            self.layer_image_data.pos_y = pos.y()
            session.add(self.layer_image_data)


class ActiveGridArea(DraggablePixmap):
    active_grid_area_color = None
    image = None

    def __init__(self, parent, rect):
        self.app = parent.app
        self.update_settings()

        super().__init__(parent, self.pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        self.app.settings_manager.changed_signal.connect(self.handle_changed_signal)

    @property
    def active_grid_area_rect(self):
        return QRect(
            self.app.settings_manager.active_grid_settings.pos_x,
            self.app.settings_manager.active_grid_settings.pos_y,
            self.app.settings_manager.settings.working_width,
            self.app.settings_manager.settings.working_height
        )

    def update_settings(self):
        border_color = self.app.settings_manager.generator.active_grid_border_color
        border_color = QColor(border_color)
        border_opacity = self.app.settings_manager.active_grid_settings.border_opacity
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
        print("active_grid_area: handle_changed_signal", key, value)
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
        elif key in [
            "active_grid_settings.enabled",
            "settings.current_tab",
            "settings.working_width",
            "settings.working_height",
        ]:
            self.redraw()

    def redraw(self):
        self.update_settings()
        scene = self.scene()
        if scene:
            scene.removeItem(self)
            if self.app.settings_manager.active_grid_settings.enabled:
                scene.addItem(self)

    def get_fill_color(self):
        fill_color = self.app.settings_manager.generator.active_grid_fill_color
        fill_color = QColor(fill_color)
        fill_opacity = self.app.settings_manager.active_grid_settings.fill_opacity
        fill_opacity = max(1, fill_opacity)
        fill_color.setAlpha(fill_opacity)
        return fill_color

    def paint(self, painter: QPainter, option, widget=None):
        if not self.app.settings_manager.active_grid_settings.render_fill:
            self.pixmap.fill(QColor(0, 0, 0, 1))

        if self.app.settings_manager.active_grid_settings.render_border:
            print(self.active_grid_area_rect)
            size = 4
            painter.setPen(QPen(
                self.active_grid_area_color,
                self.app.settings_manager.grid_settings.line_width
            ))
            painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
            painter.drawRect(self.active_grid_area_rect)
            painter.setPen(QPen(
                self.active_grid_area_color,
                self.app.settings_manager.grid_settings.line_width + 1
            ))
            painter.drawRect(QRect(
                self.active_grid_area_rect.x(),
                self.active_grid_area_rect.y(),
                self.active_grid_area_rect.width(),
                self.active_grid_area_rect.height()
            ))
        super().paint(painter, option, widget)

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


class CustomScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawing = False
        self.last_point = QPointF()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.scenePos()

    def mouseMoveEvent(self, event):
        if self.drawing:
            new_point = event.scenePos()
            self.addLine(QLineF(self.last_point, new_point), QPen(Qt.GlobalColor.red, 5))
            self.last_point = new_point

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False


class CanvasPlusWidget(CanvasBaseWidget):
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
    initialized = False
    drawing = False

    def current_pixmap(self):
        draggable_pixmap = self.current_draggable_pixmap()
        if draggable_pixmap:
            return draggable_pixmap.pixmap
    
    def current_image(self):
        pixmap = self.current_pixmap()
        if not pixmap:
            return None
        return Image.fromqpixmap(pixmap)
    
    @property
    def image_pivot_point(self):
        try:
            return QPoint(self.current_layer.pivot_x, self.current_layer.pivot_y)
        except Exception as e:
            pass
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        with session_scope() as session:
            session.add(self.current_layer)
            self.current_layer.pivot_x = value.x()
            self.current_layer.pivot_y = value.y()

    @property
    def active_grid_area_selected(self):
        return self.app.settings_manager.settings.current_tool == "active_grid_area"

    @property
    def select_selected(self):
        return self.app.settings_manager.settings.current_tool == "select"

    @property
    def eraser_selected(self):
        return self.app.settings_manager.settings.current_tool == "eraser"

    @property
    def brush_selected(self):
        return self.app.settings_manager.settings.current_tool == "brush"

    @property
    def move_selected(self):
        return self.app.settings_manager.settings.current_tool == "move"

    @property
    def brush_size(self):
        return self.app.settings_manager.settings.brush_settings.size

    @property
    def active_grid_area_rect(self):
        rect = QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.active_grid_settings.width,
            self.active_grid_settings.height
        )

        # apply self.pos_x and self.pox_y to the rect
        rect.translate(self.app.settings_manager.canvas_settings.pos_x, self.app.settings_manager.canvas_settings.pos_y)

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

    @property
    def active_grid_settings(self):
        return self.app.settings_manager.active_grid_settings
    
    @property
    def canvas_container(self):
        return self.ui.canvas_container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.settings_manager.changed_signal.connect(self.handle_changed_signal)
        with session_scope() as session:
            self.ui.central_widget.resizeEvent = self.resizeEvent
            self.app.add_image_to_canvas_signal.connect(self.handle_add_image_to_canvas)
            self.app.image_data.connect(self.handle_image_data)
            self.app.load_image.connect(self.load_image_from_path)
            self.app.load_image_object.connect(self.add_image_to_scene)
            self.initialize()
        self.app.loaded.connect(self.handle_loaded)


    
    def increase_active_grid_height(self, amount):
        height = self.app.settings_manager.settings.working_height + self.app.settings_manager.grid_settings.cell_size * amount
        if height > 4096:
            height = 4096
        self.app.settings_manager.settings.set_value("working_height", height)
        self.do_draw()
        
    def decrease_active_grid_height(self, amount):
        height = self.app.settings_manager.settings.working_height - self.app.settings_manager.grid_settings.cell_size * amount
        if height < 512:
            height = 512
        self.app.settings_manager.settings.set_value("working_height", height)
        self.do_draw()

    def increase_active_grid_width(self, amount):
        width = self.app.settings_manager.settings.working_width + self.app.settings_manager.grid_settings.cell_size * amount
        if width > 4096:
            width = 4096
        self.app.settings_manager.settings.set_value("working_width", width)
        self.do_draw()

    def decrease_active_grid_width(self, amount):
        width = self.app.settings_manager.settings.working_width - self.app.settings_manager.grid_settings.cell_size * amount
        if width < 512:
            width = 512
        self.app.settings_manager.settings.set_value("working_width", width)
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

    def handle_changed_signal(self, key, value):
        print("canvas_plus_widget: handle_changed_signal", key, value)
        if key == "settings.current_tab":
            self.do_draw()
        elif key == "settings.current_section_stablediffusion":
            self.do_draw()
        elif key == "layer_image_data.visible":
            self.do_draw()
        elif key == "layer_data.hidden":
            self.do_draw()
        elif key == "settings.active_image_editor_section":
            self.do_draw()
        elif key == "grid_settings.show_grid":
            # remove lines from scene
            for item in self.scene.items():
                if isinstance(item, QGraphicsLineItem):
                    self.scene.removeItem(item)
            self.do_draw()
    
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
        self.scene = CustomScene()

        self.view = self.canvas_container
        original_mouse_event = self.view.mouseMoveEvent
        self.view.mouseMoveEvent = partial(self.handle_mouse_event, original_mouse_event)
        #self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # # get size from self.app.ui.content_splitter which is a QSplitter
        self.view_size = self.view.viewport().size()

        # # initialize variables
        self.cell_size = self.app.settings_manager.grid_settings.cell_size
        self.line_width = self.app.settings_manager.grid_settings.line_width
        self.line_color = QColor(self.app.settings_manager.grid_settings.line_color)
        self.canvas_color = QColor(self.app.settings_manager.grid_settings.canvas_color)

        # # Set the margins of the QGraphicsView object to 0
        self.view.setContentsMargins(0, 0, 0, 0)

        self.scene.setBackgroundBrush(QBrush(self.canvas_color))
        self.view.setScene(self.scene)

        self.do_draw()

    def draw_layers(self):
        for layer in self.layers:
            image = layer.image
            if image is None:
                continue

            image = apply_opacity_to_image(
                image,
                layer.opacity / 100.0
            )

            if layer.id in self.layers:
                if not layer.visible:
                    if self.layers[layer.id] in self.scene.items():
                        self.scene.removeItem(self.layers[layer.id])
                elif layer.visible:
                    if not self.layers[layer.id] in self.scene.items():
                        self.scene.addItem(self.layers[layer.id])
                    self.layers[layer.id].pixmap.convertFromImage(ImageQt(image))
                continue

            draggable_pixmap = None
            if layer.id in self.layers:
                self.layers[layer.id].pixmap.convertFromImage(ImageQt(image))
                draggable_pixmap = self.layers[layer.id]
                self.scene.removeItem(draggable_pixmap)
            
            if not draggable_pixmap:
                draggable_pixmap = DraggablePixmap(self, QPixmap.fromImage(ImageQt(image)))
                self.layers[layer.id] = draggable_pixmap

            if layer.visible:
                self.scene.addItem(draggable_pixmap)

            pos = QPoint(layer.pos_x, layer.pos_y)
            draggable_pixmap.setPos(QPointF(
                self.app.settings_manager.canvas_settings.pos_x + pos.x(),
                self.app.settings_manager.canvas_settings.pos_y + pos.y()
            ))

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

        if self.app.settings_manager.grid_settings.show_grid:
            # vertical lines
            h = self.view_size.height() + abs(self.app.settings_manager.canvas_settings.pos_y) % self.cell_size
            y = 0
            for i in range(width_cells):
                x = i * self.cell_size + self.app.settings_manager.canvas_settings.pos_x % self.cell_size
                self.scene.addLine(x, y, x, h, pen)

            # # horizontal lines
            w = self.view_size.width() + abs(self.app.settings_manager.canvas_settings.pos_x) % self.cell_size
            x = 0
            for i in range(height_cells):
                y = i * self.cell_size + self.app.settings_manager.canvas_settings.pos_y % self.cell_size
                self.scene.addLine(x, y, w, y, pen)

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
        self.draw_lines()
        self.draw_layers()
        self.draw_active_grid_area_container()
        self.ui.canvas_position.setText(
            f"X {-self.app.settings_manager.canvas_settings.pos_x: 05d} Y {self.app.settings_manager.canvas_settings.pos_y: 05d}"
        )
        self.scene.update()
        self.drawing = False
    
    def update_cursor(self):
        # if self.is_canvas_drag_mode:
        #     # show as grab cursor
        #     self.canvas_container.setCursor(Qt.CursorShape.ClosedHandCursor)
        if self.move_selected:
            self.canvas_container.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self.active_grid_area_selected:
            self.canvas_container.setCursor(Qt.CursorShape.DragMoveCursor)
        elif self.brush_selected or self.eraser_selected:
            self.canvas_container.setCursor(
                CircleCursor(
                    Qt.GlobalColor.white,
                    Qt.GlobalColor.transparent,
                    self.brush_size
                )
            )
        else:
            self.canvas_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

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
        current_image_position = QPoint(self.current_layer.pos_x, self.current_layer.pos_y)

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
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self.load_image_from_object(image)
    
    def load_image_from_object(self, image, is_outpaint=False, image_root_point=None):
        self.add_image_to_scene(image, is_outpaint=is_outpaint, image_root_point=image_root_point)

    def load_image(self, image_path):
        image = Image.open(image_path)
        if self.app.settings_manager.settings.resize_on_paste:
            image.thumbnail((self.app.settings_manager.settings.working_width,
                             self.app.settings_manager.settings.working_height), Image.ANTIALIAS)
        self.add_image_to_scene(image)
    
    def current_draggable_pixmap(self):
        index = self.current_layer_index + 1
        if index in self.layers:
            return self.layers[index]

    def copy_image(self, image:Image=None) -> DraggablePixmap:
        pixmap = self.current_pixmap() if image is None else QPixmap.fromImage(ImageQt(image))
        return self.move_pixmap_to_clipboard(pixmap)

    def cut_image(self):
        self.copy_image()
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.scene.removeItem(draggable_pixmap)
        if self.current_layer.id in self.layers:
            del self.layers[self.current_layer.id]
        self.update()
    
    def delete_image(self):
        Logger.info("Deleting image from canvas")
        draggable_pixmap = self.current_draggable_pixmap()
        if not draggable_pixmap:
            return
        self.scene.removeItem(draggable_pixmap)
        self.update()
    
    def paste_image_from_clipboard(self):
        Logger.info("paste image from clipboard")
        image = self.get_image_from_clipboard()

        if not image:
            Logger.info("No image in clipboard")
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
            Logger.error("xclip not found. Please install xclip to copy image to clipboard.")

    def create_image(self, image):
        if self.app.settings_manager.settings.resize_on_paste:
            image = self.resize_image(image)
        self.add_image_to_scene(image)
    
    def resize_image(self, image):
        image.thumbnail(
            (
                self.app.settings_manager.settings.working_width,
                self.app.settings_manager.settings.working_height
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
        self.current_layer_index = layer_index

    def add_image_to_scene(self, image, is_outpaint=False, image_root_point=None):
        self.image_adder = ImageAdder(self, image, is_outpaint, image_root_point)
        self.image_adder.finished.connect(self.on_image_adder_finished)
        self.image_adder.start()
    
    def on_image_adder_finished(self):
        pass
    
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
