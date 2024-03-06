from typing import Optional

from PIL import ImageQt, Image
from PIL.ImageQt import QImage
from PyQt6.QtCore import Qt, QPoint, QPointF, QThread, QSize
from PyQt6.QtGui import QEnterEvent
from PyQt6.QtGui import QPainterPath
from PyQt6.QtGui import QPen, QPixmap, QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtGui import QColor
from airunner.enums import SignalCode, CanvasToolName
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.utils import snap_to_grid, convert_image_to_base64, create_worker, convert_base64_to_image
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.workers.worker import Worker


class UpdateSceneWorker(Worker):
    def __init__(self, prefix):
        super().__init__()
        self.update_time_in_ms = 0.2
        self.last_update = 0
        self.do_update = False
        self.register(SignalCode.LINES_UPDATED_SIGNAL, self.on_lines_updated_signal)

    def on_lines_updated_signal(self):
        self.do_update = True

    def handle_message(self, message):
        pass

    def run(self):
        self.running = True
        while self.running:
            if self.parent:
                self.parent.update()
            QThread.msleep(SLEEP_TIME_IN_MS)


class CustomScene(
    QGraphicsScene,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, size):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__()

        self._target_size = None
        self._do_resize = False

        # Create the QImage with the size of the parent widget
        self.image: ImageQt = Optional[None]
        self.item: QGraphicsPixmapItem = Optional[None]
        self.set_image()
        self.set_item()

        # self.item should always be on top
        self.item.setZValue(1)

        # Add a variable to store the last mouse position
        self.last_pos = None
        self.start_pos = None
        self.selection_start_pos = None
        self.selection_stop_pos = None
        self.painter = None
        self.do_update = False
        self.register(SignalCode.SCENE_RESIZE_SIGNAL, self.resize)
        self.generate_image_time_in_ms = 0.5
        self.do_generate_image = False
        self.generate_image_time = 0
        base64image = self.settings["drawing_pad_settings"]["image"]
        if base64image:
            pil_image = convert_base64_to_image(base64image).convert("RGBA")
            self.image = ImageQt.ImageQt(pil_image)

    def set_image(self):
        self.image = QImage(
            self.settings["working_width"],
            self.settings["working_height"],
            QImage.Format.Format_ARGB32
        )
        self.image.fill(Qt.GlobalColor.transparent)

    def set_item(self):
        self.item = QGraphicsPixmapItem(QPixmap.fromImage(self.image))
        self.addItem(self.item)

    @property
    def settings(self):
        return ServiceLocator.get("get_settings")()

    @settings.setter
    def settings(self, value):
        ServiceLocator.get("set_settings")(value)

    # def generate_new_image(self):
    #     self.generate_image_time = time.time()
    #     while True:
    #         if self.do_generate_image and (
    #             time.time() - self.generate_image_time >= self.generate_image_time_in_ms
    #         ):
    #             self.generate_image_time = time.time()
    #             self.emit(
    #                 SignalCode.GENERATE_IMAGE_FROM_IMAGE_SIGNAL,
    #                 self.image
    #             )
    #             self.do_generate_image = False
    #         time.sleep(0.01)

    def clear_selection(self):
        self.selection_start_pos = None
        self.selection_stop_pos = None
    
    def resize(self, size):
        """
        This function is triggered on canvas viewport resize.
        It is used to resize the pixmap which is used for drawing on the canvas.
        :param size:
        :return:
        """
        self._target_size = size
        self._do_resize = True

    def drawBackground(self, painter, rect):
        if self._do_resize:
            self._do_resize = False
            self.do_resize()

        super().drawBackground(painter, rect)

    def initialize_image(self, size=None):
        size = self._target_size if size is None else size
        if size is None:
            size = self.views()[0].size()

        # Ensure that the QPainter object has finished painting before creating a new QImage
        if self.painter is not None and self.painter.isActive():
            self.painter.end()

        self.image = QImage(
            size.width(),
            size.height(),
            QImage.Format.Format_ARGB32
        )
        self.image.fill(Qt.GlobalColor.transparent)

        self.painter = QPainter(self.image)
        return self.image

    def do_resize(self):
        size = self._target_size
        # only resize if the new size is larger than the existing image size

        if type(self.image.width) == int:
            width = self.image.width
            height = self.image.height
        else:
            width = self.image.width()
            height = self.image.height()

        if (
            width < size.width() or
            height < size.height()
        ):
            image = self.initialize_image(size)
            pixmap = QPixmap.fromImage(image)
            self.item.setPixmap(pixmap)

    def wheelEvent(self, event):
        # Calculate the zoom factor
        zoom_in_factor = self.settings["grid_settings"]["zoom_in_step"]
        zoom_out_factor = -self.settings["grid_settings"]["zoom_out_step"]

        # Use delta instead of angleDelta
        if event.delta() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        # Update zoom level
        zoom_level = self.settings["grid_settings"]["zoom_level"]
        zoom_level += zoom_factor
        if zoom_level < 0.1:
            zoom_level = 0.1
        settings = self.settings
        settings["grid_settings"]["zoom_level"] = zoom_level
        self.settings = settings

        self.emit(SignalCode.CANVAS_ZOOM_LEVEL_CHANGED)

    def handle_mouse_event(self, event, is_press_event):
        if event.button() == Qt.MouseButton.LeftButton:
            view = self.views()[0]
            pos = view.mapFromScene(event.scenePos())
            if (
                self.settings["grid_settings"]["snap_to_grid"] and
                self.settings["current_tool"] == CanvasToolName.SELECTION
            ):
                x, y = snap_to_grid(pos.x(), pos.y(), False)
                pos = QPoint(x, y)
                if is_press_event:
                    self.selection_stop_pos = None
                    self.selection_start_pos = QPoint(pos.x(), pos.y())
                else:
                    self.selection_stop_pos = QPoint(pos.x(), pos.y())
                self.emit(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED)
                self.emit(SignalCode.CANVAS_DO_DRAW_SELECTION_AREA_SIGNAL)

    def handle_left_mouse_press(self, event):
        self.start_pos = event.scenePos()
        self.handle_mouse_event(event, True)

    def handle_left_mouse_release(self, event):
        self.handle_mouse_event(event, False)

    def mousePressEvent(self, event):
        self.handle_left_mouse_press(event)
        self.handle_cursor(event)
        self.last_pos = event.scenePos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.handle_left_mouse_release(event)
        super(CustomScene, self).mouseReleaseEvent(event)
        self.handle_cursor(event)

    def handle_cursor(self, event):
        self.emit(
            SignalCode.CANVAS_UPDATE_CURSOR,
            event
        )

    def event(self, event):
        if type(event) == QEnterEvent:
            self.handle_cursor(event)
        return super(CustomScene, self).event(event)

    def mouseMoveEvent(self, event):
        self.handle_cursor(event)
    
    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super(CustomScene, self).leaveEvent(event)

