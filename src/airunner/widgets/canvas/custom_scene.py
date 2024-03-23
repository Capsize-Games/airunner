from types import NoneType
from typing import Optional

import PIL
from PIL import ImageQt, Image, ImageFilter
from PIL.ImageQt import QImage
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QEnterEvent, QDragEnterEvent, QDropEvent, QImageReader, QDragMoveEvent
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QFileDialog

from airunner.aihandler.logger import Logger
from airunner.enums import SignalCode, CanvasToolName, GeneratorSection, ServiceCode, EngineResponseCode
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.settings import VALID_IMAGE_FILES
from airunner.utils import snap_to_grid, convert_base64_to_image, convert_image_to_base64
from airunner.widgets.canvas.clipboard_handler import ClipboardHandler
from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap
from airunner.widgets.canvas.image_handler import ImageHandler
from airunner.windows.main.settings_mixin import SettingsMixin


class CustomScene(
    QGraphicsScene,
    MediatorMixin,
    SettingsMixin
):
    settings_key = "canvas_settings"

    def __init__(self, canvas_type: str):
        self.canvas_type = canvas_type
        self.logger = Logger(prefix=self.__class__.__name__)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.painter = None
        super().__init__()

        self._target_size = None
        self._do_resize = False

        # Create the QImage with the size of the parent widget
        self.image: ImageQt = Optional[None]
        self.item: QGraphicsPixmapItem = Optional[None]

        self.set_image()
        self.set_item()

        # Add a variable to store the last mouse position
        self.last_pos = None
        self.start_pos = None
        self.selection_start_pos = None
        self.selection_stop_pos = None
        self.do_update = False
        self.generate_image_time_in_ms = 0.5
        self.do_generate_image = False
        self.generate_image_time = 0

        self.signals = [
            (SignalCode.CANVAS_COPY_IMAGE_SIGNAL, self.on_canvas_copy_image_signal),
            (SignalCode.CANVAS_CUT_IMAGE_SIGNAL, self.on_canvas_cut_image_signal),
            (SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_clockwise_signal),
            (SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_counter_clockwise_signal),
            (SignalCode.CANVAS_PASTE_IMAGE_SIGNAL, self.paste_image_from_clipboard),
            (SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL, self.export_image),
            (SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL, self.import_image),
        ]
        self.register_signals()

        self.clipboard_handler = ClipboardHandler()
        self.image_handler = ImageHandler()
        ServiceLocator.register(ServiceCode.CURRENT_ACTIVE_IMAGE, self.current_active_image)
        self.register(SignalCode.CANVAS_CLEAR, self.on_canvas_clear_signal)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.split('.')[-1].lower().encode() in QImageReader.supportedImageFormats():
                self.load_image(path)

    @property
    def scene_is_active(self):
        return self.canvas_type == self.settings["canvas_settings"]["active_canvas"]

    @staticmethod
    def current_draggable_pixmap(self):
        return ServiceLocator.get(ServiceCode.CURRENT_DRAGGABLE_PIXMAP)()

    def register_signals(self):
        signals = [
            (SignalCode.CANVAS_COPY_IMAGE_SIGNAL, self.on_canvas_copy_image_signal),
            (SignalCode.CANVAS_CUT_IMAGE_SIGNAL, self.on_canvas_cut_image_signal),
            (SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_clockwise_signal),
            (SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL,
            self.on_canvas_rotate_90_counter_clockwise_signal),
            (SignalCode.CANVAS_PASTE_IMAGE_SIGNAL, self.paste_image_from_clipboard),
            (SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL, self.export_image),
            (SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL, self.import_image),
            (SignalCode.SCENE_RESIZE_SIGNAL, self.resize),
            (SignalCode.CANVAS_CANCEL_FILTER_SIGNAL, self.cancel_filter),
            (SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL, self.preview_filter),
            (SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL, self.on_load_image_from_path),
            (SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, self.on_image_generated_signal),
        ]
        for signal, handler in signals:
            self.register(signal, handler)

    def export_image(self, _message):
        image = self.current_active_image()
        if image:
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Save Image",
                "",
                f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
            )
            if file_path == "":
                return

            # If missing file extension, add it
            if not file_path.endswith(VALID_IMAGE_FILES):
                file_path = f"{file_path}.png"

            image.save(file_path)

    def import_image(self, _message):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            "",
            f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
        )
        if file_path == "":
            return
        self.load_image(file_path)

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
        self.emit_signal(SignalCode.LAYER_UPDATE_CURRENT_SIGNAL, {
            "pivot_point_x": value.x(),
            "pivot_point_y": value.y()
        })

    def paste_image_from_clipboard(self, _message):
        if self.scene_is_active:
            image = self.clipboard_handler.paste_image_from_clipboard()
            #self.delete_image()

            settings = self.settings
            if settings["resize_on_paste"]:
                image = self.resize_image(image)
            image = convert_image_to_base64(image)
            settings[self.settings_key]["image"] = image
            self.settings = settings
            self.refresh_image()

    def create_image(self, image):
        if self.settings["resize_on_paste"]:
            image = self.resize_image(image)
        if image is not None:
            self.add_image_to_scene(image)

    def resize_image(self, image: Image) -> Image:
        max_size = (self.settings["working_width"], self.settings["working_height"])
        image.thumbnail(max_size, PIL.Image.Resampling.BICUBIC)
        return image

    def on_load_image_from_path(self, message):
        image_path = message["image_path"]
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self.load_image_from_object(image)

    def load_image_from_object(
        self,
        image: Image,
        is_outpaint: bool = False
    ):
        self.add_image_to_scene(
            is_outpaint=is_outpaint,
            image=image
        )

    def load_image(self, image_path: str):
        image = self.image_handler.load_image(image_path)
        if self.settings["resize_on_paste"]:
            image = self.resize_image(image)
        self.add_image_to_scene(image)

    def cancel_filter(self, _message):
        image = self.image_handler.cancel_filter()
        if image:
            self.load_image_from_object(image=image)

    def preview_filter(self, message):
        filter_object: ImageFilter.Filter = message["filter_object"]
        filtered_image = self.image_handler.preview_filter(
            self.current_active_image(),
            filter_object
        )
        self.load_image_from_object(image=filtered_image)

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
        if is_outpaint:
            image, root_point, pivot_point = self.handle_outpaint(
                outpaint_box_rect,
                image,
                action=GeneratorSection.OUTPAINT.value
            )
        self.set_current_active_image(image)
        base64_image = convert_image_to_base64(image)
        settings = self.settings
        settings[self.settings_key]["image"] = base64_image
        self.settings = settings
        q_image = ImageQt.ImageQt(image)
        self.item.setPixmap(QPixmap.fromImage(q_image))
        self.item.setZValue(0)
        self.update()

    def current_active_image(self) -> Image:
        base_64_image = self.settings[self.settings_key]["image"]
        return convert_base64_to_image(base_64_image)

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

    def set_current_active_image(self, image: Image):
        self.logger.debug("Setting current active image")
        self.refresh_image(image)

    def refresh_image(self, image: Image = None):
        image = image if image is not None else self.current_active_image()

        # Update base64 image in settings
        base_64_image = None
        try:
            if image:
                base_64_image = convert_image_to_base64(image)
        except Exception as e:
            self.logger.error(e)
        if base_64_image is not None:
            settings = self.settings
            settings[self.settings_key]["image"] = base_64_image
            self.settings = settings

        # Update the pixmap item, image+painter and scene
        item_scene = self.item.scene() if self.item is not None else None
        if item_scene is not None:
            item_scene.removeItem(self.item)
        if self.painter and self.painter.isActive():
            self.painter.end()
        self.set_image(image)
        self.set_item()
        self.initialize_image()

    def on_image_generated_signal(self, response):
        code = response["code"]
        if code == EngineResponseCode.IMAGE_GENERATED:
            self.create_image(response["message"]["images"][0].convert("RGBA"))
        else:
            self.logger.error(f"Unhandled response code: {code}")

    def on_canvas_clear_signal(self, _message):
        settings = self.settings
        settings[self.settings_key]["image"] = None
        self.settings = settings
        self.delete_image()

    def on_canvas_copy_image_signal(self, _message):
        if self.scene_is_active:
            self.copy_image(self.current_active_image())

    def on_canvas_cut_image_signal(self, _message):
        if self.scene_is_active:
            self.cut_image(self.current_active_image())

    def on_canvas_rotate_90_clockwise_signal(self, _message):
        if self.scene_is_active:
            self.rotate_90_clockwise()

    def on_canvas_rotate_90_counter_clockwise_signal(self, _message):
        if self.scene_is_active:
            self.rotate_90_counterclockwise()

    def rotate_90_clockwise(self):
        self.rotate_image(Image.ROTATE_270)

    def rotate_90_counterclockwise(self):
        self.rotate_image(Image.ROTATE_90)

    def copy_image(
        self,
        image: Image = None
    ) -> object:
        return self.clipboard_handler.copy_image(image)

    def rotate_image(self, angle):
        image = self.image_handler.rotate_image(
            angle,
            self.current_active_image()
        )
        self.set_current_active_image(image)

    def cut_image(self, image: Image = None) -> Image:
        image = self.clipboard_handler.copy_image(image)
        if image is not None:
            self.delete_image()

    def delete_image(self):
        self.logger.debug("Deleting image from canvas")

        item_scene = self.item.scene()
        if item_scene is not None:
            item_scene.removeItem(self.item)

        if self.painter and self.painter.isActive():
            self.painter.end()
        settings = self.settings
        settings[self.settings_key]["image"] = None
        self.settings = settings
        self.image = None
        self.set_image()
        self.set_item()
        self.initialize_image()

    def set_image(self, pil_image: Image = None):
        base64image = None
        if not pil_image:
            base64image = self.settings[self.settings_key]["image"]

        if base64image is not None:
            try:
                pil_image = convert_base64_to_image(base64image).convert("RGBA")
            except AttributeError:
                self.logger.warning("Failed to convert base64 to image")

        if pil_image is not None:
            try:
                img = ImageQt.ImageQt(pil_image)
            except AttributeError as _e:
                img = None
            # img_scene = self.item.scene() if self.item is not NoneType else None
            # if img_scene is not None:
            #     img_scene.removeItem(self.item)
            self.image = img
            #self.initialize_image()
        else:
            self.image = QImage(
                self.settings["working_width"],
                self.settings["working_height"],
                QImage.Format.Format_ARGB32
            )
            self.image.fill(Qt.GlobalColor.transparent)

    def set_item(self):
        if self.image is not None:
            if self.item is NoneType:
                self.item = DraggablePixmap(QPixmap.fromImage(self.image))
                self.addItem(self.item)
            else:
                self.item.setPixmap(QPixmap.fromImage(self.image))
                if self.item.scene() is None:
                    self.addItem(self.item)
            self.item.setZValue(1)

    def clear_selection(self):
        self.selection_start_pos = None
        self.selection_stop_pos = None

    def resize(self, message):
        """
        This function is triggered on canvas viewport resize.
        It is used to resize the pixmap which is used for drawing on the canvas.

        We are currently not using this function as it was causing issues
        and may no longer be required.
        :param size:
        :return:
        """
        size = message["size"]
        # self._target_size = size
        # self._do_resize = True

        # raise the self.item and self.image to the top
        self.item.setZValue(1)

    def drawBackground(self, painter, rect):
        if self._do_resize:
            self._do_resize = False
            self.do_resize()

        super().drawBackground(painter, rect)

    def initialize_image(self):
        # Ensure that the QPainter object has finished painting before creating a new QImage
        if self.painter is not None and self.painter.isActive():
            self.painter.end()

        try:
            self.painter = QPainter(self.image)
        except TypeError as _e:
            self.logger.error("Failed to initialize painter in initialize_image")
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
            image = self.initialize_image()
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

        self.emit_signal(SignalCode.CANVAS_ZOOM_LEVEL_CHANGED)

    def handle_mouse_event(self, event, is_press_event) -> bool:
        if event.button() == Qt.MouseButton.LeftButton:
            view = self.views()[0]
            pos = view.mapFromScene(event.scenePos())
            if (
                self.settings["grid_settings"]["snap_to_grid"] and
                self.settings["current_tool"] == CanvasToolName.SELECTION
            ):
                x, y = snap_to_grid(self.settings, pos.x(), pos.y(), False)
                pos = QPoint(x, y)
                if is_press_event:
                    self.selection_stop_pos = None
                    self.selection_start_pos = QPoint(pos.x(), pos.y())
                else:
                    self.selection_stop_pos = QPoint(pos.x(), pos.y())
                self.emit_signal(SignalCode.CANVAS_DO_DRAW_SELECTION_AREA_SIGNAL)
                return True
        return False

    def handle_left_mouse_press(self, event) -> bool:
        self.start_pos = event.scenePos()
        return self.handle_mouse_event(event, True)

    def handle_left_mouse_release(self, event) -> bool:
        return self.handle_mouse_event(event, False)

    def mousePressEvent(self, event):
        if not self.handle_left_mouse_press(event):
            super(CustomScene, self).mousePressEvent(event)
        self.handle_cursor(event)
        self.last_pos = event.scenePos()
        self.update()

    def mouseReleaseEvent(self, event):
        if not self.handle_left_mouse_release(event):
            super(CustomScene, self).mouseReleaseEvent(event)
        self.handle_cursor(event)

    def event(self, event):
        if type(event) == QEnterEvent:
            self.handle_cursor(event)
        return super(CustomScene, self).event(event)

    def mouseMoveEvent(self, event):
        self.handle_cursor(event)
        super(CustomScene, self).mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.handle_cursor(event)
        super(CustomScene, self).leaveEvent(event)

    def handle_cursor(self, event):
        self.emit_signal(
            SignalCode.CANVAS_UPDATE_CURSOR,
            {
                "event": event
            }
        )

