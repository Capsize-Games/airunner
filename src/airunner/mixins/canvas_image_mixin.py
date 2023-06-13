import io
import subprocess
from PIL import Image, ImageGrab, ImageOps
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap
from airunner.models.imagedata import ImageData
from PIL.ExifTags import TAGS


class CanvasImageMixin:
    _image_data_copy = None

    @property
    def image_data(self):
        if self._image_data_copy is None:
            self._image_data_copy = self.image_data_copy(self.current_layer_index)
        return self._image_data_copy
    
    @image_data.setter
    def image_data(self, value):
        self._image_data_copy = value

    @property
    def current_active_image(self):
        try:
            return self.current_layer.image_data
        except IndexError:
            return None

    def apply_filter(self, filter):
        if self.current_layer.image_data.image is None:
            return
        self.parent.history.add_event({
            "event": "apply_filter",
            "layer_index": self.current_layer_index,
            "images": self.image_data,
        })

        if type(filter).__name__ in ["SaturationFilter", "ColorBalanceFilter", "RGBNoiseFilter", "PixelFilter"]:
            filtered_image = filter.filter(self.image_data.image)
        else:
            filtered_image = self.image_data.image.filter(filter)
        self.current_layer.image_data.image = filtered_image
        self.image_data = None

    def preview_filter(self, filter):
        if self.current_layer.image_data.image is None:
            return
        # check if filter is a SaturationFilter object
        if type(filter).__name__ in ["SaturationFilter", "ColorBalanceFilter", "RGBNoiseFilter", "PixelFilter"]:
            filtered_image = filter.filter(self.image_data.image)
        else:
            filtered_image = self.image_data.image.filter(filter)
        self.current_layer.image_data.image = filtered_image

    def cancel_filter(self):
        self.current_layer.image_data = self.image_data
        self.image_data = None

    def draw(self, layer, index):
        painter = QPainter(self.canvas_container)
        self.draw_images(layer, index, painter)
        painter.end()

    def visible_image(self, layer=None, image_data=None):
        """
        Returns an image that is cropped to the visible area of the canvas
        :param layer:
        :return: Image
        """
        if layer:
            image_data = layer.image_data

        if not image_data or not image_data.image:
            return

        # apply the layer offset
        x = image_data.position.x() + self.pos_x
        y = image_data.position.y() + self.pos_y
        location = QPoint(int(x), int(y))# + layer.offset

        rect = self.viewport_rect

        # only create a image of the visible area, apply offset
        img = image_data.image.copy().crop((rect.x() - location.x(), rect.y() - location.y(),
                        rect.x() + rect.width() - location.x(), rect.y() + rect.height() - location.y()))
        return img

    def draw_images(self, layer, index, painter):
        img = self.visible_image(layer=layer)
        if not img:
            return
        qimage = ImageQt(img)
        pixmap = QPixmap.fromImage(qimage)
        painter.drawPixmap(QPoint(0, 0), pixmap)

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
        self.current_layer.image_data = ImageData(location, image, self.current_layer.opacity)
        self.set_image_opacity(self.get_layer_opacity(self.current_layer_index))

    def invert_image(self):
        # convert image mode to RGBA
        image_data = self.current_layer.image_data
        if image_data.image is not None:
            r, g, b, a = image_data.image.split()
            r = ImageOps.invert(r)
            g = ImageOps.invert(g)
            b = ImageOps.invert(b)
            image_data.image = Image.merge("RGBA", (r, g, b, a))

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
        if self.current_layer.image_data.image is None:
            return
        image = self.current_layer.image_data.image
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

    def insert_rasterized_line_image(self, rect, img):
        processed_image, image_root_point, image_pivot_point = self.handle_outpaint(
            rect, img
        )

        self.image_root_point = image_root_point
        self.image_pivot_point = image_pivot_point
        self.add_image_to_canvas(processed_image)

    def handle_outpaint(self, outpaint_box_rect, outpainted_image, action=None):
        if self.current_layer.image_data.image is None:
            point = QPoint(outpaint_box_rect.x(), outpaint_box_rect.y())
            return outpainted_image, self.image_root_point, point

        # make a copy of the current canvas image
        existing_image_copy = self.current_layer.image_data.image.copy()
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
            "images": self.current_layer.image_data,
            "previous_image_root_point": self.image_root_point,
            "previous_image_pivot_point": self.image_pivot_point,
        })
        image = self.apply_opacity(image, self.current_layer.opacity)
        self.current_layer.image_data = ImageData(self.image_pivot_point, image, self.current_layer.opacity)

    def lower_opacity(self, i, diff):
        if i == 0:
            return 0
        total = i + diff
        return total if total > 0 else i

    def raise_opacity(self, i, diff):
        if i == 0:
            return 0
        total = i + diff
        return total

    def apply_opacity(self, image, target_opacity):
        if not image:
            return image
        target_opacity = 255 * target_opacity
        if target_opacity == 0:
            target_opacity = 1
        r, g, b, a = image.split()
        a = a.point(lambda i: target_opacity if i > 0 else 0)
        image.putalpha(a)
        return image

    def image_data_copy(self, index):
        image_data = self.layers[index].image_data
        if not image_data.image:
            return None
        return ImageData(image_data.position, image_data.image.copy(), self.current_layer.opacity)

    def rotate_90_clockwise(self):
        if self.current_active_image:
            self.parent.history.add_event({
                "event": "rotate",
                "layer_index": self.current_layer_index,
                "images": self.image_data_copy(self.current_layer_index)
            })
            self.current_active_image.image = self.current_active_image.image.transpose(Image.ROTATE_270)
            self.update()

    def rotate_90_counterclockwise(self):
        if self.current_active_image:
            self.parent.history.add_event({
                "event": "rotate",
                "layer_index": self.current_layer_index,
                "images": self.image_data_copy(self.current_layer_index)
            })
            self.current_active_image.image = self.current_active_image.image.transpose(Image.ROTATE_90)
            self.update()

    def add_image_to_canvas_new(self, image, image_pivot_point, image_root_point):
        self.parent.history.add_event({
            "event": "set_image",
            "layer_index": self.current_layer_index,
            "images": self.current_layer.image_data,
            "previous_image_root_point": image_root_point,
            "previous_image_pivot_point": image_pivot_point,
        })
        self.image_pivot_point = image_pivot_point
        self.current_layer.image_data = ImageData(image_pivot_point, image, self.current_layer.opacity)

