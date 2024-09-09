import io
import subprocess
from PIL import Image, ImageGrab
import sys

PLATFORM_WINDOWS = "windows"
PLATFORM_LINUX = "linux"
PLATFORM_BSD = "bsd"
PLATFORM_DARWIN = "darwin"
PLATFORM_UNKNOWN = "unknown"


from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap


def get_platform_name():
    if sys.platform.startswith("win"):
        return PLATFORM_WINDOWS
    elif sys.platform.startswith("darwin"):
        return PLATFORM_DARWIN
    elif sys.platform.startswith("linux"):
        return PLATFORM_LINUX
    elif sys.platform.startswith(("dragonfly", "freebsd", "netbsd", "openbsd", "bsd")):
        return PLATFORM_BSD
    else:
        return PLATFORM_UNKNOWN


__platform__ = get_platform_name()


def is_linux():
    return __platform__ == PLATFORM_LINUX


def is_bsd():
    return __platform__ == PLATFORM_BSD


def is_darwin():
    return __platform__ == PLATFORM_DARWIN


def is_windows():
    return __platform__ == PLATFORM_WINDOWS


class ClipboardHandlerMixin:
    def copy_image(
        self,
        image: Image
    ) -> DraggablePixmap:
        return self.move_pixmap_to_clipboard(image)

    def cut_image(self, image: Image) -> Image:
        image = self.copy_image(image)
        return image

    def paste_image_from_clipboard(self):
        self.logger.debug("paste image from clipboard")
        image = self.get_image_from_clipboard()

        if not image:
            self.logger.debug("No image in clipboard")
            return
        return image

    def get_image_from_clipboard(self):
        if is_windows():
            return self.image_from_system_clipboard_windows()
        return self.image_from_system_clipboard_linux()

    def move_pixmap_to_clipboard(self, image: Image) -> Image:
        if is_windows():
            return self.image_to_system_clipboard_windows(image)
        return self.image_to_system_clipboard_linux(image)

    def image_to_system_clipboard_windows(self, image: Image) -> Image:
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

    def image_from_system_clipboard_windows(self):
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
            print(e)
            return None

    def image_to_system_clipboard_linux(self, image: Image) -> Image:
        if image is None:
            return None
        data = io.BytesIO()

        # Save PIL Image to BytesIO
        image.save(data, format="png")

        data = data.getvalue()
        try:
            subprocess.Popen(["xclip", "-selection", "clipboard", "-t", "image/png"],
                             stdin=subprocess.PIPE).communicate(data)
        except FileNotFoundError:
            self.logger.error("xclip not found. Please install xclip to copy image to clipboard.")
        return image

    def image_from_system_clipboard_linux(self):
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
            print(e)
            return None
