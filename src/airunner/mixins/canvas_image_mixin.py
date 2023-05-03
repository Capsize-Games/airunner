import io
import subprocess
from PIL import Image, ImageGrab, ImageOps
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap
from airunner.models.imagedata import ImageData


class CanvasImageMixin:
    @property
    def current_active_image(self):
        try:
            return self.current_layer.images[self.current_layer_index]
        except IndexError:
            return None

    def apply_filter(self):
        index = 0
        for image in self.current_layer.images:
            self.current_layer.images[index].image = image.image.filter(self.parent.current_filter)
            index += 1

    def draw(self, layer, index):
        painter = QPainter(self.canvas_container)
        self.draw_images(layer, index, painter)
        painter.end()

    def draw_images(self, layer, index, painter):
        for image in layer.images:
            # display PIL.image as QPixmap
            img = image.image
            if self.parent.current_filter and index == self.current_layer_index:
                img = img.filter(self.parent.current_filter)
            qimage = ImageQt(img)
            pixmap = QPixmap.fromImage(qimage)

            # apply the layer offset
            x = image.position.x() + self.pos_x
            y = image.position.y() + self.pos_y
            location = QPoint(int(x), int(y)) + self.current_layer.offset

            # draw the image
            painter.drawPixmap(location, pixmap)

    def copy_image(self):
        im = self.current_active_image
        if not im:
            return
        output = io.BytesIO()
        if self.parent.is_windows:
            im.save(output, format="DIB")
            self.image_to_system_clipboard_windows(output.getvalue())
        else:
            im.save(output, format="PNG")
            self.image_to_system_clipboard_linux(output.getvalue())

    def image_to_system_clipboard_windows(self, data):
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def image_to_system_clipboard_linux(self, data):
        try:
            subprocess.Popen(["xclip", "-selection", "clipboard", "-t", "image/png"],
                             stdin=subprocess.PIPE).communicate(data)
        except FileNotFoundError:
            pass

    def image_to_system_clipboard_windows(self, data):
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def image_from_system_clipboard_windows(self):
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            win32clipboard.CloseClipboard()
            # convert bytes to image
            image = Image.open(io.BytesIO(data))
            return image
        except Exception as e:
            ErrorWindow(message=str(e))
            return None

    def image_from_system_clipboard_linux(self):
        try:
            image = ImageGrab.grabclipboard()
            # with transparency
            image = image.convert("RGBA")
            return image
        except Exception as e:
            return None

    def paste_image_from_clipboard(self):
        if self.parent.is_windows:
            image = self.image_from_system_clipboard_windows()
        else:
            image = self.image_from_system_clipboard_linux()

        if not image:
            return

        if self.settings_manager.settings.resize_on_paste.get():
            if self.settings_manager.settings.resize_on_paste.get():
                image.thumbnail((self.settings_manager.settings.working_width.get(),
                                 self.settings_manager.settings.working_height.get()), Image.ANTIALIAS)
        self.create_image(QPoint(0, 0), image)

    def create_image(self, location, image):
        """
        Create a new image object and add it to the current layer
        """
        # convert image to RGBA
        image = image.convert("RGBA")
        self.current_layer.images.append(ImageData(location, image))

    def invert_image(self):
        # convert image mode to RGBA
        for image in self.current_layer.images:
            image.image = image.image.convert("RGB")
            image.image = ImageOps.invert(image.image)
            image.image = image.image.convert("RGBA")

    def load_image(self, image_path):
        image = Image.open(image_path)

        # if settings_manager.settings.resize_on_paste, resize the image to working width and height while mainting its aspect ratio
        if self.settings_manager.settings.resize_on_paste.get():
            image.thumbnail((self.settings_manager.settings.working_width.get(), self.settings_manager.settings.working_height.get()), Image.ANTIALIAS)

        self.create_image(QPoint(0, 0), image)
        self.update()

    def save_image(self, image_path):
        image = self.current_layer.image.image
        image = image.convert("RGBA")
        image.save(image_path)
        self.saving = False
        self.update()

    def image_handler_old(self, active_img, data):
        action = data["action"]
        rect: QRect = data["options"]["outpaint_box_rect"]
        rect: QRect = data["options"]["outpaint_box_rect"]
        x = rect.x()
        y = rect.y()
        if len(self.current_layer.images) > 0:
            # merge with previous image
            image = self.current_layer.images[0].image
            image.paste(active_img, (int(x), int(y)))
            self.current_layer.images = [ImageData(QPoint(int(x), int(y)), image)]
        else:
            self.current_layer.images = [ImageData(QPoint(int(x), int(y)), active_img)]
        self.current_layer.lines = []
        self.update()

    def image_handler(self, active_img, data):
        self.update_image_canvas(data["action"], data, active_img)
        self.current_layer.lines = []
        self.update()

    def update_image_canvas(self, section=None, data=None, processed_image: Image = None):
        """
        Update the image by section
        This is used by other classes to add an image to the canvas
        :param section: the section (action) that was taken to generate this image. section is a deprecated name
        :param data: the data to update the image with
        :param processed_image: the image to update the canvas with
        :return:
        """
        processed_image = processed_image.convert("RGBA")
        section = data["action"] if not section else section
        outpaint_box_rect = data["options"]["outpaint_box_rect"]
        processed_image, image_root_point, image_pivot_point = self.handle_outpaint(
            outpaint_box_rect, processed_image, section
        )

        self.image_root_point = image_root_point
        self.image_pivot_point = image_pivot_point
        self.add_image_to_canvas(processed_image)

    def add_image_to_canvas(self, image):
        self.parent.history.add_event({
            "event": "set_image",
            "layer_index": self.current_layer_index,
            "images": self.current_layer.images,
            "previous_image_root_point": self.image_root_point,
            "previous_image_pivot_point": self.image_pivot_point,
        })
        self.current_layer.images = [ImageData(self.image_pivot_point, image)]

    def get_image_copy(self, index):
        return [ImageData(imageData.position, imageData.image.copy()) for imageData in self.layers[index].images]