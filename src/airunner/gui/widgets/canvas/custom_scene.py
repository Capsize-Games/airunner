import io
import os
import subprocess
from typing import Optional, Tuple, Dict

import PIL
from PIL import ImageQt, Image, ImageFilter, ImageGrab
from PySide6.QtGui import QImage
from PySide6.QtCore import Qt, QPoint, QRect, QPointF
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import (
    QEnterEvent,
    QDragEnterEvent,
    QDropEvent,
    QImageReader,
    QDragMoveEvent,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QGraphicsScene,
    QFileDialog,
    QGraphicsSceneMouseEvent,
    QMessageBox,
)

from airunner.enums import SignalCode, CanvasToolName, EngineResponseCode
from airunner.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.settings import (
    AIRUNNER_VALID_IMAGE_FILES,
    AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE,
)
from airunner.utils import is_windows
from airunner.utils.image import (
    export_image,
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.stablediffusion.rect import Rect
from airunner.handlers.stablediffusion.image_response import ImageResponse
from airunner.utils.settings.get_qsettings import get_qsettings


class CustomScene(
    MediatorMixin,
    SettingsMixin,
    QGraphicsScene,
):
    def __init__(self, canvas_type: str):
        self._is_erasing = None
        self._is_drawing = None
        self.canvas_type = canvas_type
        self.image_backup = None
        self.previewing_filter = False
        self.painter = None
        self.image: Optional[QImage] = None
        self.item: Optional[DraggablePixmap] = None
        self._image_initialized: bool = False
        super().__init__()
        self.last_export_path = None
        self._target_size = None
        self.settings = get_qsettings()

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
        self._original_item_positions = {}  # Store original positions of items

        # Add viewport rectangle that includes negative space
        self._extended_viewport_rect = QRect(-2000, -2000, 4000, 4000)

        for signal, handler in [
            (
                SignalCode.CANVAS_COPY_IMAGE_SIGNAL,
                self.on_canvas_copy_image_signal,
            ),
            (
                SignalCode.CANVAS_CUT_IMAGE_SIGNAL,
                self.on_canvas_cut_image_signal,
            ),
            (
                SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL,
                self.on_canvas_rotate_90_clockwise_signal,
            ),
            (
                SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL,
                self.on_canvas_rotate_90_counterclockwise_signal,
            ),
            (
                SignalCode.CANVAS_PASTE_IMAGE_SIGNAL,
                self.on_paste_image_from_clipboard,
            ),
            (
                SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL,
                self.on_export_image_signal,
            ),
            (
                SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL,
                self.on_import_image_signal,
            ),
            (
                SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
                self.on_send_image_to_canvas_signal,
            ),
            (
                SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
                self.on_apply_filter_signal,
            ),
            (
                SignalCode.CANVAS_CANCEL_FILTER_SIGNAL,
                self.on_cancel_filter_signal,
            ),
            (
                SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
                self.on_preview_filter_signal,
            ),
            (
                SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL,
                self.on_load_image_from_path,
            ),
            (
                SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
                self.on_image_generated_signal,
            ),
            (SignalCode.UNDO_SIGNAL, self.on_action_undo_signal),
            (SignalCode.REDO_SIGNAL, self.on_action_redo_signal),
            (SignalCode.HISTORY_CLEAR_SIGNAL, self.on_clear_history_signal),
            (SignalCode.CANVAS_CLEAR, self.on_canvas_clear_signal),
            (SignalCode.MASK_LAYER_TOGGLED, self.on_mask_layer_toggled),
            (
                SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
                self.on_settings_changed,
            ),
        ]:
            self.register(signal, handler)

    @property
    def current_tool(self):
        return CanvasToolName(self.application_settings.current_tool)

    @property
    def settings_key(self):
        return self.property("settings_key")

    @property
    def current_settings(self):
        settings = None
        if self.settings_key == "controlnet_settings":
            settings = self.controlnet_settings
        elif self.settings_key == "image_to_image_settings":
            settings = self.image_to_image_settings
        elif self.settings_key == "outpaint_settings":
            settings = self.outpaint_settings
        elif self.settings_key == "drawing_pad_settings":
            settings = self.drawing_pad_settings
        if not settings:
            raise ValueError(
                f"Settings is not set. Settings not found for key: {self.settings_key}"
            )
        return settings

    @property
    def image_pivot_point(self):
        return QPoint(self.current_settings.x_pos, self.current_settings.y_pos)

    @property
    def current_active_image(self) -> Image:
        base_64_image = self.current_settings.image
        try:
            return convert_binary_to_image(base_64_image)
        except PIL.UnidentifiedImageError:
            return None

    @current_active_image.setter
    def current_active_image(self, image: Image):
        if image is not None:
            image = convert_image_to_binary(image)
        self._update_current_settings("image", image)
        if self.settings_key == "drawing_pad_settings":
            self.api.art.canvas.image_updated()

    @property
    def is_brush_or_eraser(self):
        return self.current_tool in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER,
        )

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        self.api.art.canvas.update_current_layer(value)

    def on_clear_history_signal(self):
        self._clear_history()

    def on_export_image_signal(self):
        image = self.current_active_image
        if image:
            # Set the parent window to the main application window
            parent_window = self.views()[0].window()

            # Use the last export path if available
            initial_dir = (
                self.last_export_path if self.last_export_path else ""
            )

            file_dialog = QFileDialog(
                parent_window,
                "Save Image",
                initial_dir,
                f"Image Files ({' '.join(AIRUNNER_VALID_IMAGE_FILES)})",
            )
            file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
                file_path = file_dialog.selectedFiles()[0]
                if file_path == "":
                    return

                # Update the last export path
                self.last_export_path = os.path.dirname(file_path)

                # If missing file extension, add it
                if not file_path.endswith(AIRUNNER_VALID_IMAGE_FILES):
                    file_path = f"{file_path}.png"

                export_image(image, file_path)

    def on_import_image_signal(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            "",
            f"Image Files ({' '.join(AIRUNNER_VALID_IMAGE_FILES)})",
        )
        if file_path == "":
            return
        self.on_load_image_signal(file_path)

    def on_send_image_to_canvas_signal(self, data: Dict):
        image_response: ImageResponse = data.get("image_response")
        image = image_response.images[0]
        self.initialize_image(image)

    def on_paste_image_from_clipboard(self):
        image = self._paste_image_from_clipboard()
        if image is None:
            return
        if self.application_settings.resize_on_paste:
            image = self._resize_image(image)
        if type(image) is not bytes:
            binary_image = convert_image_to_binary(image)
        self.current_active_image = binary_image
        if type(image) is not bytes:
            self.refresh_image(image)

    def on_load_image_from_path(self, message):
        image_path = message["image_path"]
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self._load_image_from_object(image)

    def on_load_image_signal(self, image_path: str):
        self._add_image_to_undo()
        image = self._load_image(image_path)
        if self.application_settings.resize_on_paste:
            image = self._resize_image(image)
        self.current_active_image = image
        self.initialize_image(image)

    def on_apply_filter_signal(self, message):
        self._apply_filter(message)

    def on_cancel_filter_signal(self):
        image = self._cancel_filter()
        if image:
            self._load_image_from_object(image=image)

    def on_preview_filter_signal(self, message):
        filter_object: ImageFilter.Filter = message["filter_object"]
        filtered_image = self._preview_filter(
            self.current_active_image, filter_object
        )
        self._load_image_from_object(image=filtered_image)

    def on_image_generated_signal(self, data: Dict):
        code = data["code"]
        callback = data.get("callback", None)

        if code in (
            EngineResponseCode.INSUFFICIENT_GPU_MEMORY,
            EngineResponseCode.ERROR,
        ):
            if self.settings_key == "drawing_pad_settings":
                message = data.get("message")
                self.api.application_error(message)
                self.display_gpu_memory_error(message)
        elif code is EngineResponseCode.INTERRUPTED:
            pass
        elif code is EngineResponseCode.IMAGE_GENERATED:
            self._handle_image_generated_signal(data)
        else:
            if self.settings_key == "drawing_pad_settings":
                self.logger.error(f"Unhandled response code: {code}")

        if self.settings_key == "drawing_pad_settings":
            self.api.art.stop_progress_bar()
            if callback:
                callback(data)

    def _handle_image_generated_signal(self, data: Dict):
        image_response: Optional[ImageResponse] = data.get("message", None)
        if image_response is None:
            self.logger.error("No message received from engine")
            return
        images = image_response.images
        if len(images) == 0:
            self.logger.debug("No images received from engine")
        elif image_response:
            outpaint_box_rect = image_response.active_rect
            self._create_image(
                image=images[0].convert("RGBA"),
                is_outpaint=image_response.is_outpaint,
                outpaint_box_rect=outpaint_box_rect,
            )

    def display_gpu_memory_error(self, message: str):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error: Unable to Generate Image")
        msg_box.setText(message)

        enable_cpu_offload_button = None
        if message == AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE:
            enable_cpu_offload_button = msg_box.addButton(
                "Enable CPU offload", QMessageBox.ButtonRole.AcceptRole
            )

        msg_box.exec()

        if (
            enable_cpu_offload_button
            and msg_box.clickedButton() == enable_cpu_offload_button
        ):
            self.enable_cpu_offload_callback()

    def enable_cpu_offload_callback(self):
        self.update_memory_settings("enable_model_cpu_offload", True)

    def on_canvas_clear_signal(self):
        self.current_active_image = None
        self.delete_image()
        self._clear_history()

    def on_mask_layer_toggled(self):
        self.initialize_image()

    def on_settings_changed(self, data):
        table = data["setting_name"]
        column_name = data["column_name"]
        value = data["value"]
        # if table == "controlnet_settings" and column_name == "generated_image":

    def on_canvas_copy_image_signal(self):
        self._copy_image(self.current_active_image)

    def on_canvas_cut_image_signal(self):
        self._cut_image(self.current_active_image)

    def on_canvas_rotate_90_clockwise_signal(self):
        self._rotate_90_clockwise()

    def on_canvas_rotate_90_counterclockwise_signal(self):
        self._rotate_90_counterclockwise()

    def on_action_undo_signal(self):
        if len(self.undo_history) == 0:
            return
        data = self.undo_history.pop()
        self._add_image_to_redo()
        self._history_set_image(data)

    def on_action_redo_signal(self):
        if len(self.redo_history) == 0:
            return
        data = self.redo_history.pop()
        self._add_image_to_undo()
        self._history_set_image(data)

    def _history_set_image(self, data: Dict):
        if data is not None:
            if data["image"] is None:
                self.delete_image()
            else:
                self.current_active_image = data["image"]
                self.initialize_image(self.current_active_image)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._image_initialized:
            self._image_initialized = True
            self.initialize_image()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if (
                path.split(".")[-1].lower().encode()
                in QImageReader.supportedImageFormats()
            ):
                self._load_image(path)

    def wheelEvent(self, event):
        if not hasattr(event, "delta"):
            return

        # Check if the Ctrl key is pressed
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = self.grid_settings.zoom_in_step
            zoom_out_factor = -self.grid_settings.zoom_out_step

            if event.delta() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor

            # Update zoom level
            zoom_level = self.grid_settings.zoom_level
            zoom_level += zoom_factor
            if zoom_level < 0.1:
                zoom_level = 0.1
            self.update_grid_settings("zoom_level", zoom_level)
            self.api.art.canvas.zoom_level_changed()

    def mousePressEvent(self, event):
        if isinstance(event, QGraphicsSceneMouseEvent):
            if event.button() == Qt.MouseButton.RightButton:
                self.right_mouse_button_pressed = True
                self.start_pos = event.scenePos()
            elif event.button() == Qt.MouseButton.LeftButton:
                super(CustomScene, self).mousePressEvent(event)
        self._handle_cursor(event)
        self.last_pos = event.scenePos()
        self.update()

        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_left_mouse_press(event)
            self._handle_cursor(event)
            if not self.is_brush_or_eraser:
                super().mousePressEvent(event)
            elif self.drawing_pad_settings.enable_automatic_drawing:
                self.api.art.canvas.interrupt_image_generation()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_mouse_button_pressed = False
        else:
            self._handle_left_mouse_release(event)
            super(CustomScene, self).mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)
        self._handle_cursor(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_pos = None
            self.start_pos = None
            self.do_update = False
            if self.drawing_pad_settings.enable_automatic_drawing:
                if self._is_drawing or self._is_erasing:
                    self.api.art.generate_image()
            self._is_drawing = False
            self._is_erasing = False

    def mouseMoveEvent(self, event):
        if self.right_mouse_button_pressed:
            view = self.views()[0]
            view.setTransformationAnchor(view.ViewportAnchor.NoAnchor)
            view.setResizeAnchor(view.ViewportAnchor.NoAnchor)
            delta = event.scenePos() - self.last_pos
            scale_factor = (
                view.transform().m11()
            )  # Get the current scale factor
            view.translate(delta.x() / scale_factor, delta.y() / scale_factor)
            self.last_pos = event.scenePos()
        else:
            super(CustomScene, self).mouseMoveEvent(event)

        self.last_pos = event.scenePos()
        self.update()

    def enterEvent(self, event):
        self._handle_cursor(event, True)

    def leaveEvent(self, event):
        self._handle_cursor(event, False)

    def refresh_image(self, image: Image = None):
        # Save the current viewport position
        view = self.views()[0]
        current_viewport_rect = view.mapToScene(
            view.viewport().rect()
        ).boundingRect()

        # End the painter if it is active
        if self.painter and self.painter.isActive():
            self.painter.end()

        # Update the pixmap item, image+painter and scene
        try:
            item_scene = self.item.scene()
        except AttributeError:
            item_scene = None
        if item_scene is not None:
            item_scene.removeItem(self.item)
        self.initialize_image(image)
        # Restore the viewport position

        view.setSceneRect(current_viewport_rect)

    def delete_image(self):
        self.logger.debug("Deleting image from canvas")
        item_scene = self.item.scene()
        if item_scene is not None:
            item_scene.removeItem(self.item)

        if self.painter and self.painter.isActive():
            self.painter.end()
        self.current_active_image = None
        self.image = None
        del self.item
        self.item = None

    def set_image(self, pil_image: Image = None):
        base64image = None
        if not pil_image:
            base64image = self.current_settings.image

        if base64image is not None:
            try:
                pil_image = convert_binary_to_image(base64image).convert(
                    "RGBA"
                )
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
            self.image = img
        else:
            self.image = QImage(
                self.application_settings.working_width,
                self.application_settings.working_height,
                QImage.Format.Format_ARGB32,
            )
            self.image.fill(Qt.GlobalColor.transparent)

    def set_item(
        self, image: QImage = None, z_index: int = 5
    ):  # Change default z_index to 5
        # Instead of fixed scene rect, use extended viewport
        self.setSceneRect(self._extended_viewport_rect)

        if image is not None:
            if self.item is None:
                self.item = LayerImageItem(image)
                if self.item.scene() is None:
                    self.addItem(self.item)
                    # Store initial position when adding to scene
                    self._original_item_positions[self.item] = self.item.pos()
            else:
                self.item.updateImage(image)

            self.item.setZValue(
                z_index
            )  # Higher Z-value for better visibility

            # Ensure item is visible and prepare its geometry
            self.item.setVisible(True)

    def clear_selection(self):
        self.selection_start_pos = None

    def clear_selection(self):
        self.selection_start_pos = None
        self.selection_stop_pos = None

    def initialize_image(self, image: Image = None):
        """Initialize the image in the scene."""
        self.stop_painter()
        self.set_image(image)

        # Save the current position before updating the item
        old_pos = self.item.pos() if self.item else QPointF(0, 0)

        if self.item is not None:
            x = self.image_pivot_point.x()
            y = self.image_pivot_point.y()
        else:
            x = self.active_grid_settings.pos_x
            y = self.active_grid_settings.pos_y

        self.set_item(self.image)

        self.set_painter(self.image)

        # If we had an original position stored for the previous item, use it for the new item
        if self.item is not None:
            # set position to active grid area
            if self.item is not None:
                self.item.setPos(
                    x,
                    y,
                )
                self.api.art.canvas.update_image_positions()

            # Store the position if not already tracked
            if self.item not in self._original_item_positions:
                # Use the old position if it was a replacement item
                if old_pos != QPointF(0, 0):
                    self._original_item_positions[self.item] = old_pos
                else:
                    self._original_item_positions[self.item] = self.item.pos()

            # Make sure item is visible with priority rendering
            self.item.setVisible(True)
            self.item.setZValue(5)

            # Force immediate update of the image area
            self.update(self.item.boundingRect())

            # Make sure the view's viewport also gets updated
            if self.views():
                self.views()[0].viewport().update()
                QApplication.processEvents()

    def stop_painter(self):
        if self.painter is not None and self.painter.isActive():
            self.painter.end()

    def set_painter(self, image: QImage):
        if image is None:
            return
        try:
            self.painter = QPainter(image)
        except TypeError as _e:
            self.logger.error(
                "Failed to initialize painter in initialize_image"
            )

    def _update_current_settings(self, key, value):
        if self.settings_key == "controlnet_settings":
            self.update_controlnet_settings(key, value)
        elif self.settings_key == "image_to_image_settings":
            self.update_image_to_image_settings(key, value)
        elif self.settings_key == "outpaint_settings":
            self.update_outpaint_settings(key, value)
        elif self.settings_key == "drawing_pad_settings":
            self.update_drawing_pad_settings(key, value)

    def _load_image_from_object(self, image: Image, is_outpaint: bool = False):
        self._add_image_to_scene(is_outpaint=is_outpaint, image=image)

    def _paste_image_from_clipboard(self):
        self.logger.debug("paste image from clipboard")
        image = self._get_image_from_clipboard()

        if not image:
            self.logger.debug("No image in clipboard")
            return
        return image

    def _get_image_from_clipboard(self):
        if is_windows():
            return self._image_from_system_clipboard_windows()
        return self._image_from_system_clipboard_linux()

    def _image_from_system_clipboard_windows(self):
        self.logger.debug("image_from_system_clipboard_windows")
        import win32clipboard

        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            win32clipboard.CloseClipboard()
            # convert bytes to image
            image = Image.open(io.BytesIO(data))
            return image
        except Exception as e:
            self.logger.error(f"Failed to get image from clipboard: {e}")
            return None

    def _image_from_system_clipboard_linux(self):
        self.logger.debug("image_from_system_clipboard_linux")
        try:
            image = ImageGrab.grabclipboard()
            if not image:
                self.logger.debug("No image in clipboard")
                return None
            # with transparency
            image = image.convert("RGBA")
            return image
        except Exception as e:
            self.logger.error(f"Failed to get image from clipboard: {e}")
            return None

    def _copy_image(self, image: Image) -> Image:
        return self._move_pixmap_to_clipboard(image)

    def _move_pixmap_to_clipboard(self, image: Image) -> Image:
        if is_windows():
            return self._image_to_system_clipboard_windows(image)
        return self._image_to_system_clipboard_linux(image)

    def _image_to_system_clipboard_windows(self, image: Image) -> Image:
        if image is None:
            return None
        self.logger.debug("image_to_system_clipboard_windows")
        import win32clipboard

        data = io.BytesIO()
        image.save(data, format="png")
        data = data.getvalue()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return image

    def _image_to_system_clipboard_linux(self, image: Image) -> Image:
        if image is None:
            return None
        data = io.BytesIO()

        # Save PIL Image to BytesIO
        image.save(data, format="png")

        data = data.getvalue()
        try:
            subprocess.Popen(
                ["xclip", "-selection", "clipboard", "-t", "image/png"],
                stdin=subprocess.PIPE,
            ).communicate(data)
        except FileNotFoundError:
            self.logger.error(
                "xclip not found. Please install xclip to copy image to clipboard."
            )
        return image

    def _create_image(
        self,
        image: Image.Image,
        is_outpaint: bool,
        outpaint_box_rect: Optional[Rect] = None,
    ):
        if self.application_settings.resize_on_paste:
            image = self._resize_image(image)

        if image is not None:
            self._add_image_to_scene(
                image,
                is_outpaint=is_outpaint,
                outpaint_box_rect=outpaint_box_rect,
            )
            # Emit signal to notify the view to update image positions
            self.api.art.canvas.image_updated()

    def _resize_image(self, image: Image) -> Image:
        if image is None:
            return

        max_size = (
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        image.thumbnail(max_size, PIL.Image.Resampling.BICUBIC)
        return image

    def _add_image_to_scene(
        self,
        image: Image.Image,
        is_outpaint: bool = False,
        outpaint_box_rect: Optional[Rect] = None,
    ):
        """
        Adds a given image to the scene
        :param image: Image object to add to the scene
        :param is_outpaint: bool indicating if the image is an outpaint
        :param outpaint_box_rect: Rect indicating the root point of the image
        :return:
        """
        # image = ImageOps.expand(image, border=border_size, fill=border_color)
        if image is None:
            self.logger.warning("Image is None, unable to add to scene")
            return

        # Get the current canvas offset from the view
        canvas_offset = self.get_canvas_offset()

        # Check for existing stored position in drawing_pad_settings
        settings_x = self.drawing_pad_settings.x_pos
        settings_y = self.drawing_pad_settings.y_pos

        if outpaint_box_rect:
            if is_outpaint:
                image, root_point, _pivot_point = self._handle_outpaint(
                    outpaint_box_rect, image
                )
            else:
                root_point = QPoint(outpaint_box_rect.x, outpaint_box_rect.y)
        elif settings_x is not None and settings_y is not None:
            root_point = QPoint(settings_x, settings_y)
        else:
            root_point = QPoint(0, 0)

        q_image = ImageQt.ImageQt(image)

        # Use updateImage method instead of setPixmap
        if self.item:
            self.item.updateImage(q_image)
            self.item.setZValue(0)
        else:
            # If there's no item yet, create one first
            self.set_item(q_image, z_index=5)

        # Always update the stored absolute position in the scene
        if self.item:
            # Store the absolute position without any adjustments
            absolute_pos = QPointF(root_point.x(), root_point.y())
            self._original_item_positions[self.item] = absolute_pos

            # Calculate display position by subtracting current canvas offset
            visible_pos_x = absolute_pos.x() - canvas_offset.x()
            visible_pos_y = absolute_pos.y() - canvas_offset.y()
            self.item.setPos(visible_pos_x, visible_pos_y)

        self.update()
        self.initialize_image(image)
        self.current_active_image = image

    def _handle_outpaint(
        self, outpaint_box_rect: Rect, outpainted_image: Image
    ) -> Tuple[Image.Image, QPoint, QPoint]:
        if self.current_active_image is None:
            point = QPoint(outpaint_box_rect.x, outpaint_box_rect.y)
            return outpainted_image, QPoint(0, 0), point

        # make a copy of the current canvas image
        existing_image_copy = self.current_active_image.copy()
        width = existing_image_copy.width
        height = existing_image_copy.height

        pivot_point = self.image_pivot_point
        root_point = QPoint(0, 0)
        current_image_position = QPoint(0, 0)

        is_drawing_left = outpaint_box_rect.x < current_image_position.x()
        is_drawing_right = outpaint_box_rect.x > current_image_position.x()
        is_drawing_up = outpaint_box_rect.y < current_image_position.y()
        is_drawing_down = outpaint_box_rect.y > current_image_position.y()

        x_pos = outpaint_box_rect.x
        y_pos = outpaint_box_rect.y
        outpaint_width = outpaint_box_rect.width
        outpaint_height = outpaint_box_rect.height

        if is_drawing_right:
            if x_pos + outpaint_width > width:
                width = x_pos + outpaint_width

        if is_drawing_down:
            if y_pos + outpaint_height > height:
                height = y_pos + outpaint_height

        if is_drawing_up:
            height += current_image_position.y()
            root_point.setY(outpaint_box_rect.y)

        if is_drawing_left:
            width += current_image_position.x()
            root_point.setX(outpaint_box_rect.x)

        new_dimensions = (width, height)

        new_image = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_a = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_b = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))

        image_root_point = QPoint(root_point.x(), root_point.y())
        image_pivot_point = QPoint(pivot_point.x(), pivot_point.y())

        new_image_a.paste(
            outpainted_image,
            (int(outpaint_box_rect.x), int(outpaint_box_rect.y())),
        )
        new_image_b.paste(
            existing_image_copy,
            (current_image_position.x(), current_image_position.y()),
        )

        # Convert mask to binary mask
        mask_image = self.drawing_pad_mask
        mask = mask_image.convert("L").point(lambda p: p > 128 and 255)
        inverted_mask = Image.eval(mask, lambda p: 255 - p)
        # create a new mask with new_dimensions which is all white and
        # paste the inverted mask into it.
        pos_x = outpaint_box_rect.x
        pos_y = outpaint_box_rect.y
        if pos_x < 0:
            pos_x = 0
        if pos_y < 0:
            pos_y = 0
        new_mask = Image.new("L", new_dimensions, 255)
        new_mask.paste(inverted_mask, (pos_x, pos_y))
        new_image_b = Image.composite(
            new_image_b, Image.new("RGBA", new_image_b.size), new_mask
        )

        new_image = Image.alpha_composite(new_image, new_image_a)
        new_image = Image.alpha_composite(new_image, new_image_b)

        return new_image, image_root_point, image_pivot_point

    def _set_current_active_image(self, image: Image):
        self.logger.debug("Setting current active image")
        self.initialize_image(image)

    def _rotate_90_clockwise(self):
        self.rotate_image(-90)

    def _rotate_90_counterclockwise(self):
        self.rotate_image(90)

    def rotate_image(self, angle: float):
        image = self.current_active_image
        if image is not None:
            self._add_image_to_undo()
            image = image.rotate(angle, expand=True)
            self.current_active_image = image
            self.initialize_image(image)

    def _add_undo_history(self, data: Dict):
        self.undo_history.append(data)

    def _add_redo_history(self, data: Dict):
        self.redo_history.append(data)

    def _clear_history(self):
        self.undo_history = []
        self.redo_history = []
        self.api.art.canvas.clear_history()

    def _cut_image(self, image: Image = None) -> Image:
        image = self._copy_image(image)
        if image is not None:
            self._add_image_to_undo(image)
            self.delete_image()

    def _add_image_to_undo(self, image: Image = None):
        image = self.current_active_image if image is None else image
        self._add_undo_history({"image": image if image is not None else None})
        self.api.art.canvas.update_history(
            len(self.undo_history), len(self.redo_history)
        )

    def _add_image_to_redo(self):
        image = self.current_active_image
        self._add_redo_history({"image": image if image is not None else None})
        self.api.art.canvas.update_history(
            len(self.undo_history), len(self.redo_history)
        )

    def _handle_left_mouse_press(self, event):
        try:
            self.start_pos = event.scenePos()
        except AttributeError:
            self.logger.error("Failed to get scenePos from left click event")

    def _handle_left_mouse_release(self, event):
        pass

    def _handle_cursor(self, event, apply_cursor: bool = True):
        # Track the last cursor state to avoid redundant calls
        if hasattr(self, "_last_cursor_state"):
            # Add position to the tracked state to debounce cursor updates during small movements
            current_state = (event.type(), apply_cursor)

            # Only process if the event type or apply_cursor changed
            # This significantly reduces cursor update processing
            if self._last_cursor_state == current_state:
                return

        # Update the tracked state
        self._last_cursor_state = (event.type(), apply_cursor)

        # Instead of creating a complex message object, let's modify the event if needed
        # This ensures compatibility with the API expecting (event, apply_cursor)
        evt = event

        # If this is an enter/leave event that doesn't have .button() method,
        # we need to create a simplified event object that works with the cursor logic
        if not hasattr(event, "button"):
            # Create a simple object with the necessary properties
            class SimpleEvent:
                def __init__(self, original_event):
                    self.type_value = original_event.type()
                    # Add properties that _update_cursor will check
                    self.button_value = None
                    self.buttons_value = Qt.MouseButton.NoButton

                def type(self):
                    return self.type_value

                def button(self):
                    return self.button_value

                def buttons(self):
                    return self.buttons_value

            # Create our simplified event
            evt = SimpleEvent(event)

        # Call the API with the expected parameters
        self.api.art.canvas.update_cursor(evt, apply_cursor)

    @staticmethod
    def _load_image(image_path: str) -> Image:
        image = Image.open(image_path)
        return image

    def _apply_filter(self, _filter_object: ImageFilter.Filter):
        if self.settings_key != "drawing_pad_settings":
            return
        self._add_image_to_undo(self.image_backup)
        self.previewing_filter = False
        self.image_backup = None

    def _cancel_filter(self) -> Image:
        image = None
        if self.image_backup:
            image = self.image_backup.copy()
            self.image_backup = None
        self.previewing_filter = False
        return image

    def _preview_filter(self, image: Image, filter_object: ImageFilter.Filter):
        if self.settings_key != "drawing_pad_settings":
            return
        if not image:
            return
        if not self.previewing_filter:
            self.image_backup = image.copy()
            self.previewing_filter = True
        else:
            image = self.image_backup.copy()
        filtered_image = filter_object.filter(image)
        return filtered_image

    def update_image_position(self, canvas_offset):
        """Update the position of image items in the scene based on the canvas offset."""
        if not self.item:
            return

        # Store the original position if we haven't already
        if self.item not in self._original_item_positions:
            # Use the drawing_pad_settings values for position
            abs_x = self.drawing_pad_settings.x_pos
            abs_y = self.drawing_pad_settings.y_pos

            if abs_x is None or abs_y is None:
                # Default to current position if settings aren't available
                abs_x = self.item.pos().x() + canvas_offset.x()
                abs_y = self.item.pos().y() + canvas_offset.y()

            self._original_item_positions[self.item] = QPointF(abs_x, abs_y)

        # Get the original absolute position
        original_pos = self._original_item_positions[self.item]

        # Calculate and set the new position
        new_x = original_pos.x() - canvas_offset.x()
        new_y = original_pos.y() - canvas_offset.y()

        # Before changing position, prepare the item for geometry change
        self.item.prepareGeometryChange()
        self.item.setPos(new_x, new_y)

        # Make sure the item is visible and in focus
        self.item.setVisible(True)
        self.item.setZValue(5)  # Priority rendering

        # Update the entire viewport to ensure image is visible even at negative coordinates
        self.invalidate(
            self._extended_viewport_rect, QGraphicsScene.SceneLayer.ItemLayer
        )

    def get_canvas_offset(self):
        """Get the current canvas offset from the parent view if available."""
        if self.views() and hasattr(self.views()[0], "canvas_offset"):
            return self.views()[0].canvas_offset
        return QPointF(0, 0)
