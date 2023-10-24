import math
from functools import partial

from PIL import Image
from PIL.ImageQt import ImageQt, QImage
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QPainter, QCursor
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsPixmapItem, QGraphicsLineItem

from airunner.aihandler.settings_manager import SettingsManager
from airunner.cursors.circle_brush import CircleCursor
from airunner.data.db import session
from airunner.data.models import Layer, LayerImage, CanvasSettings, ActiveGridSettings
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
    def current_layer(self):
        return self.app.ui.layer_widget.current_layer

    @property
    def current_layer_index(self):
        return self.app.ui.layer_widget.current_layer_index

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.canvas_settings = session.query(CanvasSettings).first()
        self.active_grid_settings = session.query(ActiveGridSettings).first()
        self.ui.central_widget.resizeEvent = self.resizeEvent
        self.app.add_image_to_canvas_signal.connect(self.handle_add_image_to_canvas)
        self.app.image_data.connect(self.handle_image_data)
        self.initialize()

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

        # # Set the size of the QGraphicsScene object to match the size of the QGraphicsView object
        self.settings_manager.changed_signal.connect(self.handle_changed_signal)

        self.do_draw()

    def draw_layers(self):
        session = get_session()
        layers = session.query(Layer).filter(
            Layer.document_id == self.app.document.id,
        ).order_by(
            Layer.position.asc()
        ).all()
        for layer in layers:
            if layer.id in self.layers:
                for image in self.layers[layer.id]:
                    self.scene.removeItem(image)
            else:
                self.layers[layer.id] = []
            images = session.query(LayerImage).filter(
                LayerImage.layer_id == layer.id
            ).order_by(
                LayerImage.order.asc()
            ).all()
            for layer_image in images:
                image = layer_image.image
                pixmap = QPixmap.fromImage(ImageQt(image))
                image = LayerImageItem(self, pixmap, layer_image)
                self.layers[layer.id].append(image)
                if layer_image.visible and not layer.hidden:
                    self.scene.addItem(image)
                pos = QPoint(layer_image.pos_x, layer_image.pos_y)
                image.setPos(QPointF(
                    self.canvas_settings.pos_x + pos.x(),
                    self.canvas_settings.pos_y + pos.y()
                ))

    def handle_changed_signal(self, key, value):
        if key == "current_tab":
            self.draw_layers()
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
        self.view_size = self.view.viewport().size()
        self.set_scene_rect()
        self.draw_lines()
        self.draw_layers()
        self.draw_active_grid_area_container()
        self.ui.canvas_position.setText(
            f"X {-self.canvas_settings.pos_x: 05d} Y {self.canvas_settings.pos_y: 05d}"
        )

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
        image = data["image"]
        image_data = data["data"]
        # add image to the canvas
        pixmap = QPixmap.fromImage(ImageQt(image))
        image = DraggablePixmap(self, pixmap)
        self.scene.addItem(image)
        # image.setPos(QPointF(
        #     self.canvas_settings.pos_x + data.pos_x,
        #     self.canvas_settings.pos_y + data.pos_y
        # ))

    def load_image(self, image_path):
        image = Image.open(image_path)

        if self.app.settings_manager.resize_on_paste:
            image.thumbnail((self.settings_manager.working_width,
                             self.settings_manager.working_height), Image.ANTIALIAS)

        pixmap = QPixmap.fromImage(ImageQt(image))
        image = DraggablePixmap(self, pixmap)
        self.scene.addItem(image)

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

    def preview_filter(self, filter):
        if len(self.current_layer.image_data) == 0:
            return
        for image_data in self.current_layer.image_data:
            image = image_data.image
            if self.filter_with_filter:
                filtered_image = filter.filter(image)
            else:
                filtered_image = image.filter(filter)
            image_data.image = filtered_image
    
    def cancel_filter(self):
        for index in range(len(self.current_layer.image_data)):
            self.current_layer.image_data[index] = self.image_data[index]
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
            self.current_layer.image_data[index].image = filtered_image
            self.image_data = []