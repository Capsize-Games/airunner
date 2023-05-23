import io
import subprocess
from PIL import Image, ImageGrab, ImageOps
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap
from airunner.models.imagedata import ImageData
from PIL.ExifTags import TAGS


class CanvasImageMixin:
    _working_images = None

    @property
    def working_images(self):
        if self._working_images is None:
            self._working_images = self.get_image_copy(self.current_layer_index)
        return self._working_images
    
    @working_images.setter
    def working_images(self, value):
        self._working_images = value

    @property
    def current_active_image(self):
        try:
            return self.current_layer.images[0]
        except IndexError:
            return None

    def apply_filter(self, filter):
        if len(self.current_layer.images) == 0:
            return
        self.parent.history.add_event({
            "event": "apply_filter",
            "layer_index": self.current_layer_index,
            "images": self.working_images,
        })
        for n in range(0, len(self.working_images)):
            if type(filter).__name__ in ["SaturationFilter", "ColorBalanceFilter", "RGBNoiseFilter"]:
                filtered_image = filter.filter(self.working_images[n].image.copy())
            else:
                filtered_image = self.working_images[n].image.copy().filter(filter)
            self.current_layer.images[n].image = filtered_image
        self.working_images = None

    def preview_filter(self, filter):
        if self.current_layer.images and len(self.current_layer.images) == 0:
            return
        for n in range(0, len(self.working_images)):
            # check if filter is a SaturationFilter object
            if type(filter).__name__ in ["SaturationFilter", "ColorBalanceFilter", "RGBNoiseFilter"]:
                filtered_image = filter.filter(self.working_images[n].image.copy())
            else:
                filtered_image = self.working_images[n].image.copy().filter(filter)
            self.current_layer.images[n].image = filtered_image

    def cancel_filter(self):
        self.current_layer.images = self.working_images
        self.working_images = None

    def draw(self, layer, index):
        painter = QPainter(self.canvas_container)
        self.draw_images(layer, index, painter)
        painter.end()

    def draw_images(self, layer, index, painter):
        if not layer.images:
            return
        for image in layer.images:
            # display PIL.image as QPixmap
            img = image.image
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
            im.image.save(output, format="DIB")
            self.image_to_system_clipboard_windows(output.getvalue())
        else:
            im.image.save(output, format="PNG")
            self.image_to_system_clipboard_linux(output.getvalue())

    def image_to_system_clipboard_windows(self, data):
        import win32clipboard
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
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def image_from_system_clipboard_windows(self):
        import win32clipboard
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
        self.update()

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
        self.load_metadata(image)

        # if settings_manager.settings.resize_on_paste, resize the image to working width and height while mainting its aspect ratio
        if self.settings_manager.settings.resize_on_paste.get():
            image.thumbnail((self.settings_manager.settings.working_width.get(), self.settings_manager.settings.working_height.get()), Image.ANTIALIAS)

        self.create_image(QPoint(0, 0), image)
        self.update()

    def load_metadata(self, image):
        if not self.settings_manager.settings.import_metadata.get():
            return
        try:
            metadata = image.text
        except AttributeError:
            metadata = None
        self.parent.load_metadata(metadata)

    def save_image(self, image_path):
        if self.current_layer.image is None:
            return
        image = self.current_layer.image.image
        image = image.convert("RGBA")
        if not "." in image_path:
            image_path += ".png"
        if not image_path.endswith(".png") and not image_path.endswith(".gif"):
            image = image.convert("RGB")
        image.save(image_path)
        self.saving = False
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

    def handle_outpaint(self, outpaint_box_rect, outpainted_image, action):
        if len(self.current_layer.images) == 0:
            point = QPoint(outpaint_box_rect.x(), outpaint_box_rect.y())
            return outpainted_image, self.image_root_point, point

        # make a copy of the current canvas image
        existing_image_copy = self.current_layer.images[0].image.copy()
        width = existing_image_copy.width
        height = existing_image_copy.height
        working_width = outpainted_image.width
        working_height = outpainted_image.height

        is_drawing_left = outpaint_box_rect.x() < self.image_pivot_point.x()
        is_drawing_up = outpaint_box_rect.y() < self.image_pivot_point.y()

        if is_drawing_left:
            # get the x overlap of the outpaint box and the image
            x_overlap = min(width, outpaint_box_rect.width()) - max(0, outpaint_box_rect.x())
        else:
            # get the x overlap of the outpaint box and the image
            x_overlap = min(width, outpaint_box_rect.width()) - max(0, outpaint_box_rect.x() - self.image_pivot_point.x())

        if is_drawing_up:
            # get the y overlap of the outpaint box and the image
            y_overlap = min(height, outpaint_box_rect.height()) - max(0, outpaint_box_rect.y())
        else:
            # get the y overlap of the outpaint box and the image
            y_overlap = min(height, outpaint_box_rect.height()) - max(0, outpaint_box_rect.y() - self.image_pivot_point.y())

        # get the x and y overlap of the outpaint box and the image
        new_dimensions = (int(width + working_width - x_overlap), int(height + working_height - y_overlap))
        if new_dimensions[0] < width:
            new_dimensions = (width, new_dimensions[1])
        if new_dimensions[1] < height:
            new_dimensions = (new_dimensions[0], height)
        new_image = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_a = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_b = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        existing_image_pos = [0, 0]
        image_root_point = QPoint(self.image_root_point.x(), self.image_root_point.y())
        image_pivot_point = QPoint(self.image_pivot_point.x(), self.image_pivot_point.y())
        if is_drawing_left:
            current_x_pos = abs(outpaint_box_rect.x() - image_pivot_point.x())
            left_overlap = abs(outpaint_box_rect.x()) - abs(image_root_point.x())
            image_root_point.setX(width + left_overlap)
            image_pivot_point.setX(int(outpaint_box_rect.x()))
            existing_image_pos = [current_x_pos, existing_image_pos[1]]
            pos_x = max(0, outpaint_box_rect.x() + self.image_pivot_point.x())
        else:
            pos_x = max(0, outpaint_box_rect.x() - self.image_pivot_point.x())
        if is_drawing_up:
            current_y_pos = abs(outpaint_box_rect.y() - image_pivot_point.y())
            up_overlap = abs(outpaint_box_rect.y()) - abs(image_root_point.y())
            image_root_point.setY(height + up_overlap)
            image_pivot_point.setY(int(outpaint_box_rect.y()))
            existing_image_pos = [existing_image_pos[0], current_y_pos]
            pos_y = max(0, outpaint_box_rect.y() + self.image_pivot_point.y())
        else:
            pos_y = max(0, outpaint_box_rect.y() - self.image_pivot_point.y())

        new_image_a.paste(outpainted_image, (int(pos_x), int(pos_y)))
        new_image_b.paste(existing_image_copy, (int(existing_image_pos[0]), int(existing_image_pos[1])))

        if action == "outpaint":
            new_image = Image.alpha_composite(new_image, new_image_a)
            new_image = Image.alpha_composite(new_image, new_image_b)
        else:
            new_image = Image.alpha_composite(new_image, new_image_b)
            new_image = Image.alpha_composite(new_image, new_image_a)

        return new_image, image_root_point, image_pivot_point

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

    def rotate_90_clockwise(self):
        if self.current_active_image:
            self.parent.history.add_event({
                "event": "rotate",
                "layer_index": self.current_layer_index,
                "images": self.get_image_copy(self.current_layer_index)
            })
            self.current_active_image.image = self.current_active_image.image.transpose(Image.ROTATE_270)
            self.update()

    def rotate_90_counterclockwise(self):
        if self.current_active_image:
            self.parent.history.add_event({
                "event": "rotate",
                "layer_index": self.current_layer_index,
                "images": self.get_image_copy(self.current_layer_index)
            })
            self.current_active_image.image = self.current_active_image.image.transpose(Image.ROTATE_90)
            self.update()
