import io
import subprocess

from PIL import Image, ImageGrab
from PIL.ImageQt import ImageQt
from PyQt6.QtGui import QPixmap
from watchdog.utils.platform import is_windows

from airunner.aihandler.logger import Logger
from airunner.mediator_mixin import MediatorMixin
from airunner.widgets.canvas.draggables import DraggablePixmap
from airunner.windows.main.settings_mixin import SettingsMixin


class ClipboardHandler(
    SettingsMixin,
    MediatorMixin
):
    def __init__(self):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.logger = Logger(prefix=self.__class__.__name__)

    def copy_image(
            self,
            image: Image = None,
            draggable_pixmap: DraggablePixmap = None
    ) -> DraggablePixmap:
        pixmap = draggable_pixmap if image is None else QPixmap.fromImage(ImageQt(image))
        if not pixmap:
            return None
        return self.move_pixmap_to_clipboard(pixmap)

    def cut_image(self) -> DraggablePixmap:
        draggable_pixmap = self.copy_image()
        return draggable_pixmap

    def paste_image_from_clipboard(self):
        self.logger.info("paste image from clipboard")
        image = self.get_image_from_clipboard()

        if not image:
            self.logger.info("No image in clipboard")
            return
        return image

    def get_image_from_clipboard(self):
        if is_windows():
            return self.image_from_system_clipboard_windows()
        return self.image_from_system_clipboard_linux()

    def move_pixmap_to_clipboard(self, pixmap):
        if is_windows():
            return self.image_to_system_clipboard_windows(pixmap)
        return self.image_to_system_clipboard_linux(pixmap)

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
        return pixmap

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
        return pixmap

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