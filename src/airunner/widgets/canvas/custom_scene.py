import os
from types import NoneType
from typing import Optional

import PIL
from PIL import ImageQt, Image, ImageFilter
from PIL.ImageQt import QImage
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QEnterEvent, QDragEnterEvent, QDropEvent, QImageReader, QDragMoveEvent, QMouseEvent
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QFileDialog, QGraphicsSceneMouseEvent

from airunner.aihandler.logger import Logger
from airunner.enums import SignalCode, CanvasToolName, GeneratorSection, EngineResponseCode
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import VALID_IMAGE_FILES
from airunner.utils.snap_to_grid import snap_to_grid
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.utils.convert_image_to_base64 import convert_image_to_base64
from airunner.widgets.canvas.mixins.clipboard_handler_mixin import ClipboardHandlerMixin
from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap
from airunner.widgets.canvas.mixins.image_handler_mixin import ImageHandlerMixin
from airunner.windows.main.settings_mixin import SettingsMixin


class CustomScene(
    QGraphicsScene,
    MediatorMixin,
    SettingsMixin,
    ImageHandlerMixin,
    ClipboardHandlerMixin
):
    settings_key = "canvas_settings"

    def __init__(self, canvas_type: str):
        self.canvas_type = canvas_type
        self.logger = Logger(prefix=self.__class__.__name__)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        ImageHandlerMixin.__init__(self)
        ClipboardHandlerMixin.__init__(self)
        self.painter = None
        self.image: ImageQt = Optional[None]
        self.item: QGraphicsPixmapItem = Optional[None]
        super().__init__()
        self.last_export_path = None
        self._target_size = None
        self._do_resize = False

        # Add a variable to store the last mouse position
        self.last_pos = None
        self.start_pos = None
        self.selection_start_pos = None
        self.selection_stop_pos = None
        self.do_update = False
        self.generate_image_time_in_ms = 0.5
        self.do_generate_image = False
        self.generate_image_time = 0
        self.undo_history = []
        self.redo_history = []
        self.right_mouse_button_pressed = False
        self.handling_event = False

        self.register_signals()

        self.register(SignalCode.CANVAS_CLEAR, self.on_canvas_clear_signal)

    def showEvent(self, event):
        self.set_image()
        self.set_item()

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

    def register_signals(self):
        signals = [
            (SignalCode.CANVAS_COPY_IMAGE_SIGNAL, self.on_canvas_copy_image_signal),
            (SignalCode.CANVAS_CUT_IMAGE_SIGNAL, self.on_canvas_cut_image_signal),
            (SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_clockwise_signal),
            (SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_counter_clockwise_signal),
            (SignalCode.CANVAS_PASTE_IMAGE_SIGNAL, self.on_paste_image_from_clipboard),
            (SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL, self.export_image),
            (SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL, self.import_image),
            (SignalCode.CANVAS_CANCEL_FILTER_SIGNAL, self.handle_cancel_filter),
            (SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL, self.handle_preview_filter),
            (SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL, self.on_load_image_from_path),
            (SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, self.on_image_generated_signal),
            (SignalCode.UNDO_SIGNAL, self.action_undo_triggered),
            (SignalCode.REDO_SIGNAL, self.action_redo_triggered),
            (SignalCode.HISTORY_CLEAR_SIGNAL, self.clear_history),
        ]
        for signal, handler in signals:
            self.register(signal, handler)

    def export_image(self):
        image = self.current_active_image()
        if image:
            # Set the parent window to the main application window
            parent_window = self.views()[0].window()

            # Use the last export path if available
            initial_dir = self.last_export_path if self.last_export_path else ""

            file_dialog = QFileDialog(parent_window, "Save Image", initial_dir, f"Image Files ({' '.join(VALID_IMAGE_FILES)})")
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            if file_dialog.exec() == QFileDialog.Accepted:
                file_path = file_dialog.selectedFiles()[0]
                if file_path == "":
                    return

                # Update the last export path
                self.last_export_path = os.path.dirname(file_path)

                # If missing file extension, add it
                if not file_path.endswith(VALID_IMAGE_FILES):
                    file_path = f"{file_path}.png"

                # Save the combined image
                image.save(file_path)

    def import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            "",
            f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
        )
        if file_path == "":
            return
        self.handle_load_image(file_path)

    def current_layer(self):
        # TODO
        return None

    @property
    def image_pivot_point(self):
        try:
            layer = self.current_layer()
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

    def on_paste_image_from_clipboard(self):
        if self.scene_is_active:
            image = self.paste_image_from_clipboard()
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
        if image is None:
            return
        settings = self.settings
        max_size = (settings["working_width"], settings["working_height"])
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

    def handle_load_image(self, image_path: str):
        image = self.load_image(image_path)
        if self.settings["resize_on_paste"]:
            image = self.resize_image(image)
        self.add_image_to_scene(image)

    def handle_cancel_filter(self):
        image = self.cancel_filter()
        if image:
            self.load_image_from_object(image=image)

    def handle_preview_filter(self, message):
        filter_object: ImageFilter.Filter = message["filter_object"]
        filtered_image = self.preview_filter(
            self.current_active_image(),
            filter_object
        )
        self.load_image_from_object(image=filtered_image)

    def add_image_to_scene(
        self,
        image: Image,
        is_outpaint: bool = False,
        outpaint_box_rect: QPoint = None,
        border_size: int = 1,  # size of the border
        border_color: tuple = (255, 0, 0, 255)  # color of the border in RGBA format
    ):
        """
        Adds a given image to the scene
        :param image_data: dict containing the image to be added to the scene
        :param is_outpaint: bool indicating if the image is an outpaint
        :param outpaint_box_rect: QPoint indicating the root point of the image
        :param border_size: int indicating the size of the border
        :param border_color: tuple indicating the color of the border
        :return:
        """
        # image = ImageOps.expand(image, border=border_size, fill=border_color)

        if image is None:
            self.logger.warning("Image is None, unable to add to scene")
            return

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
        try:
            return convert_base64_to_image(base_64_image)
        except PIL.UnidentifiedImageError:
            return None

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
        layer = self.current_layer()
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

        # Save the current viewport position
        view = self.views()[0]
        current_viewport_rect = view.mapToScene(view.viewport().rect()).boundingRect()

        # Update the pixmap item, image+painter and scene
        try:
            item_scene = self.item.scene()
        except AttributeError:
            item_scene = None
        if item_scene is not None:
            item_scene.removeItem(self.item)
        if self.painter and self.painter.isActive():
            self.painter.end()
        self.set_image(image)
        self.set_item()
        self.initialize_image()

        # Restore the viewport position
        view.setSceneRect(current_viewport_rect)

    def on_image_generated_signal(self, response):
        code = response["code"]
        if code == EngineResponseCode.IMAGE_GENERATED:
            message = response["message"]
            if message is None:
                self.logger.error("No message received from engine")
                return
            images = message["images"]
            if len(images) == 0:
                self.logger.debug("No images received from engine")
            elif message:
                self.create_image(images[0].convert("RGBA"))
        else:
            self.logger.error(f"Unhandled response code: {code}")
        self.emit_signal(SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL)

    def on_canvas_clear_signal(self):
        settings = self.settings
        settings[self.settings_key]["image"] = None
        self.settings = settings
        self.delete_image()

    def on_canvas_copy_image_signal(self):
        if self.scene_is_active:
            self.copy_image(self.current_active_image())

    def on_canvas_cut_image_signal(self):
        if self.scene_is_active:
            self.cut_image(self.current_active_image())

    def on_canvas_rotate_90_clockwise_signal(self):
        self.rotate_90_clockwise()

    def on_canvas_rotate_90_counter_clockwise_signal(self):
        self.rotate_90_counterclockwise()

    def rotate_90_clockwise(self):
        self.rotate_image(-90)

    def rotate_90_counterclockwise(self):
        self.rotate_image(90)

    def __add_undo_history(self, data: dict):
        self.undo_history.append(data)

    def __add_redo_history(self, data: dict):
        self.redo_history.append(data)

    def __clear_history(self):
        self.undo_history = []
        self.redo_history = []

    def action_undo_triggered(self):
        if len(self.undo_history) == 0:
            return
        data = self.undo_history.pop()
        self.__add_image_to_redo()
        self.history_set_image(data)

    def action_redo_triggered(self):
        if len(self.redo_history) == 0:
            return
        data = self.redo_history.pop()
        self.__add_image_to_undo()
        self.history_set_image(data)

    def rotate_image(self, angle):
        self.__add_image_to_undo()
        image = self.current_active_image()
        if image is not None:
            image = image.rotate(angle, expand=True)
            self.refresh_image(image)
        else:
            self.logger.warning("No image to rotate")

    def cut_image(self, image: Image = None) -> Image:
        image = self.copy_image(image)
        if image is not None:
            self.__add_image_to_undo()
            self.delete_image()

    def history_set_image(self, data: dict):
        if data is not None:
            self.refresh_image(data["image"])

    def clear_history(self):
        self.__clear()

    def __add_image_to_undo(self):
        image = self.current_active_image()
        if image is not None:
            self.__add_undo_history({
                "image": image.copy()
            })

    def __add_image_to_redo(self):
        image = self.current_active_image()
        if image is not None:
            self.__add_redo_history({
                "image": image.copy()
            })

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
        settings = self.settings
        base64image = None
        if not pil_image:
            base64image = settings[self.settings_key]["image"]

        if base64image is not None:
            try:
                pil_image = convert_base64_to_image(base64image).convert("RGBA")
            except AttributeError:
                self.logger.warning("Failed to convert base64 to image")
            except PIL.UnidentifiedImageError:
                pil_image = None

        if pil_image is not None:
            try:
                img = ImageQt.ImageQt(pil_image)
            except AttributeError as _e:
                img = None
            except IsADirectoryError:
                img = None
            # img_scene = self.item.scene() if self.item is not NoneType else None
            # if img_scene is not None:
            #     img_scene.removeItem(self.item)
            self.image = img
            #self.initialize_image()
        else:
            self.image = QImage(
                settings["working_width"],
                settings["working_height"],
                QImage.Format.Format_ARGB32
            )
            self.image.fill(Qt.GlobalColor.transparent)

    def set_item(self):
        self.setSceneRect(0, 0, 512, 512)
        if self.image is not None:
            image = self.image
            if self.item is NoneType:
                self.item = DraggablePixmap(QPixmap.fromImage(image))
                self.item.setZValue(1)
                self.addItem(self.item)
            else:
                self.item.setPixmap(QPixmap.fromImage(image))
                self.item.setZValue(1)
                if self.item.scene() is None:
                    self.addItem(self.item)

    def clear_selection(self):
        self.selection_start_pos = None
        self.selection_stop_pos = None

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
        if not hasattr(event, "delta"):
            return

        # Check if the Ctrl key is pressed
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            settings = self.settings
            zoom_in_factor = settings["grid_settings"]["zoom_in_step"]
            zoom_out_factor = -settings["grid_settings"]["zoom_out_step"]

            if event.delta() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor

            # Update zoom level
            zoom_level = settings["grid_settings"]["zoom_level"]
            zoom_level += zoom_factor
            if zoom_level < 0.1:
                zoom_level = 0.1
            settings["grid_settings"]["zoom_level"] = zoom_level
            self.settings = settings

            self.emit_signal(SignalCode.CANVAS_ZOOM_LEVEL_CHANGED)

    def handle_mouse_event(self, event, is_press_event) -> bool:
        if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
            settings = self.settings
            view = self.views()[0]
            pos = view.mapFromScene(event.scenePos())
            if (
                settings["grid_settings"]["snap_to_grid"] and
                settings["current_tool"] == CanvasToolName.SELECTION
            ):
                x, y = snap_to_grid(settings, pos.x(), pos.y(), False)
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
        try:
            self.start_pos = event.scenePos()
        except AttributeError:
            self.logger.error("Failed to get scenePos from left click event")
        return self.handle_mouse_event(event, True)

    def handle_left_mouse_release(self, event) -> bool:
        return self.handle_mouse_event(event, False)

    def mousePressEvent(self, event):
        if isinstance(event, QGraphicsSceneMouseEvent):
            if event.button() == Qt.MouseButton.RightButton:
                self.right_mouse_button_pressed = True
                self.start_pos = event.scenePos()
            elif not self.handle_left_mouse_press(event):
                super(CustomScene, self).mousePressEvent(event)
        self.handle_cursor(event)
        self.last_pos = event.scenePos()
        self.update()

    def mouseMoveEvent(self, event):
        if self.right_mouse_button_pressed:
            view = self.views()[0]
            view.setTransformationAnchor(view.ViewportAnchor.NoAnchor)
            view.setResizeAnchor(view.ViewportAnchor.NoAnchor)
            delta = event.scenePos() - self.last_pos
            scale_factor = view.transform().m11()  # Get the current scale factor
            view.translate(delta.x() / scale_factor, delta.y() / scale_factor)
            self.last_pos = event.scenePos()
        else:
            self.handle_cursor(event)
            super(CustomScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_mouse_button_pressed = False
        elif not self.handle_left_mouse_release(event):
            super(CustomScene, self).mouseReleaseEvent(event)
        self.handle_cursor(event)

    def event(self, event):
        if self.handling_event:
            return False  # Prevent recursive event calls

        self.handling_event = True
        try:
            if type(event) == QEnterEvent:
                self.handle_cursor(event)
            return super(CustomScene, self).event(event)
        finally:
            self.handling_event = False

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

