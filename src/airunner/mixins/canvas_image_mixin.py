import io
import random
import subprocess
from PIL import Image, ImageGrab, ImageOps
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap
from PIL.ImageFilter import GaussianBlur
from airunner.filters.rgb_noise_filter import RGBNoiseFilter
from airunner.models.imagedata import ImageData
from PIL.ExifTags import TAGS
from airunner.models.layerdata import LayerData


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
    def current_active_image_data(self):
        try:
            return self.current_layer.image_data
        except IndexError:
            return None

    def initialize(self):
        pass

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
        self.draw_images(layer, painter)
        painter.end()

    def visible_image(self, layer=None, image_data=None):
        """
        Returns an image that is cropped to the visible area of the canvas
        :param layer:
        :return: Image
        """
        if layer:
            image_data = layer.image_data

        if not image_data:
            return

        img = image_data.image
        if not img:
            return

        # apply the layer offset
        x = image_data.position.x() + self.pos_x
        y = image_data.position.y() + self.pos_y
        location = QPoint(int(x), int(y))# + layer.offset

        rect = self.viewport_rect

        # only create a image of the visible area, apply offset
        img = img.copy().crop((
            rect.x() - location.x(),
            rect.y() - location.y(),
            rect.x() + rect.width() - location.x(),
            rect.y() + rect.height() - location.y()
        ))
        return img

    def draw_images(self, layer, painter):
        img = self.visible_image(layer=layer)
        if img:
            offset = layer.offset
            qimage = ImageQt(img)
            pixmap = QPixmap.fromImage(qimage)
            painter.drawPixmap(QPoint(0, 0), pixmap)
            # painter.drawPixmap(offset, pixmap)

    def copy_image(self):
        im = self.current_active_image_data
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
            #self.parent.error_handler(str(e))
            print(e)
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
        self.current_layer.image_data = ImageData(
            position=location,
            image=image,
            opacity=self.current_layer.opacity
        )
        #self.set_image_opacity(self.get_layer_opacity(self.current_layer_index))

    def invert_image(self):
        # convert image mode to RGBA
        image_data = self.current_layer.image_data
        if image_data.image is not None:
            r, g, b, a = image_data.image.split()
            r = ImageOps.invert(r)
            g = ImageOps.invert(g)
            b = ImageOps.invert(b)
            image_data.image = Image.merge("RGBA", (r, g, b, a))

    def film_filter(self):
        working_images = self.parent.canvas.current_active_image_data
        if working_images.image is not None:
            self.parent.history.add_event({
                "event": "apply_filter",
                "layer_index": self.current_layer_index,
                "images": self.image_data,
            })
            image = working_images.image.copy()
            red_grain = Image.new("L", image.size)
            green_grain = Image.new("L", image.size)
            blue_grain = Image.new("L", image.size)
            red_grain.putdata([random.randint(0, 255) for _i in range(image.size[0] * image.size[1])])
            green_grain.putdata([random.randint(0, 255) for _i in range(image.size[0] * image.size[1])])
            blue_grain.putdata([random.randint(0, 255) for _i in range(image.size[0] * image.size[1])])
            filter = RGBNoiseFilter(0.1, 0.1, 0.1, red_grain, green_grain, blue_grain)
            filtered_image = filter.filter(self.image_data.image)
            filtered_image = filtered_image.filter(GaussianBlur(radius=0.03 * 20))
            self.current_layer.image_data.image = filtered_image
            self.image_data = None
        self.update()

    def load_image(self, image_path):
        image = Image.open(image_path)

        # if settings_manager.settings.resize_on_paste, resize the image to working width and height while mainting its aspect ratio
        if self.settings_manager.settings.resize_on_paste.get():
            image.thumbnail((self.settings_manager.settings.working_width.get(), self.settings_manager.settings.working_height.get()), Image.ANTIALIAS)

        self.create_image(QPoint(0, 0), image)
        self.update()

    def save_image(self, image_path, image=None):
        if self.current_layer.image_data.image is None:
            return
        if image is None:
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
        if section not in["superresolution", "upscale"]:
            processed_image, image_root_point, image_pivot_point = self.handle_outpaint(
                outpaint_box_rect,
                processed_image,
                section,
                is_kandinsky=data["options"].get("generator_section") == "kandinsky"
            )
        else:
            # if we are upscaling (or using superresolution) we want to replace the existing image with the new
            # one so that there is no undesired overlapping of images.
            # to do this, the handle_outpaint function is skipped and we reset the coordinates to 0,0
            image_root_point = QPoint(0, 0)
            image_pivot_point = QPoint(0, 0)
            self.pos_x = 0
            self.pos_y = 0

        processed_data = {
            "processed_image": processed_image,
            "image_root_point": image_root_point,
            "image_pivot_point": image_pivot_point,
            "add_image_to_canvas": True
        }

        """
        We pass data through an emitter so that it can be modified by other classes and adding to canvas
        can be interrupted if needed. For example, the image interpolation window takes the processed image
        and displays it in the window rather than on the canvas.
        """
        self.parent.add_image_to_canvas_signal.emit(processed_data)
        is_deterministic = data["options"][f"deterministic_generation"]
        if processed_data["add_image_to_canvas"] and (not is_deterministic or data["force_add_to_canvas"]):
            self.add_image_to_canvas(
                processed_data["processed_image"],
                image_root_point=processed_data["image_root_point"],
                image_pivot_point=processed_data["image_pivot_point"]
            )
        elif is_deterministic:
            self.deterministic_images = processed_data["images"]
            self.open_deterministic_window()

    def insert_rasterized_line_image(self, rect: QRect, img: Image, layer: LayerData):
        existing_image = layer.image_data.image
        # combine img with existing image
        pos = [0, 0]
        if existing_image is None:
            point = QPoint(rect.x(), rect.y())
            width = img.width
            height = img.height
            new_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        else:
            point = QPoint(
                min(rect.x(), layer.image_data.position.x()),
                min(rect.y(), layer.image_data.position.y())
            )
            if point.x() < rect.x():
                pos[0] = abs(point.x()) + rect.x()
            if point.y() < rect.y():
                pos[1] = abs(point.y()) + rect.y()
            existing_position = layer.image_data.position
            is_drawing_left = rect.x() < existing_position.x()
            is_drawing_right = rect.width() > (existing_image.width + existing_position.x())
            is_drawing_top = rect.y() < existing_position.y()
            is_drawing_bottom = rect.height() > (existing_image.height + existing_position.y())

            x_overlap = 0
            if is_drawing_left:
                x_overlap = existing_position.x() - rect.x()
            if is_drawing_right:
                x_overlap += rect.width() - (existing_image.width + existing_position.x())
            y_overlap = 0
            if is_drawing_top:
                y_overlap = existing_position.y() - rect.y()
            if is_drawing_bottom:
                y_overlap += rect.height() - (existing_image.height + existing_position.y())

            if is_drawing_left or is_drawing_right:
                width = existing_image.width + x_overlap
            else:
                width = max(existing_image.width, img.width)
            if is_drawing_top or is_drawing_bottom:
                height = existing_image.height + y_overlap
            else:
                height = max(existing_image.height, img.height)
            new_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        if existing_image:
            pos_x = layer.image_data.position.x() - rect.x() if rect.x() < layer.image_data.position.x() else 0
            pos_y = layer.image_data.position.y() - rect.y() if rect.y() < layer.image_data.position.y() else 0
            new_image.alpha_composite(existing_image, (pos_x, pos_y))
        new_image.alpha_composite(img, (pos[0], pos[1]))
        self.add_image_to_canvas(
            new_image,
            image_root_point=point,
            image_pivot_point=point,
            layer=layer
        )

    def handle_outpaint(self, outpaint_box_rect, outpainted_image, action=None, is_kandinsky=False):
        if self.current_layer.image_data.image is None:
            point = QPoint(outpaint_box_rect.x(), outpaint_box_rect.y())
            return outpainted_image, self.image_root_point, point

        # make a copy of the current canvas image
        existing_image_copy = self.current_layer.image_data.image.copy()
        width = existing_image_copy.width
        height = existing_image_copy.height

        pivot_point = self.image_pivot_point
        root_point = self.image_root_point
        current_image_position = self.current_layer.image_data.position

        is_drawing_left = outpaint_box_rect.x() < pivot_point.x()
        is_drawing_right = outpaint_box_rect.width() > (width + current_image_position.x())
        is_drawing_up = outpaint_box_rect.y() < pivot_point.y()
        is_drawing_down = outpaint_box_rect.height() > (height + current_image_position.y())

        image_left = pivot_point.x()
        image_right = width + image_left
        image_top = pivot_point.y()
        image_bottom = height + image_top
        outpaint_box_right = outpaint_box_rect.width()
        outpaint_box_left = outpaint_box_rect.x()
        outpaint_box_top = outpaint_box_rect.y()
        outpaint_box_bottom = outpaint_box_rect.height()

        x_overlap = 0
        if is_drawing_left:
            x_overlap = image_left - outpaint_box_left
        if is_drawing_right:
            x_overlap += outpaint_box_right - image_right

        y_overlap = 0
        if is_drawing_up:
            y_overlap = image_top - outpaint_box_top
        if is_drawing_down:
            y_overlap += outpaint_box_bottom - image_bottom

        if is_drawing_left or is_drawing_right:
            x = width + x_overlap
        else:
            x = width
        if is_drawing_up or is_drawing_down:
            y = height + y_overlap
        else:
            y = height
        new_dimensions = (int(x), int(y))
        if new_dimensions[0] < width:
            new_dimensions = (width, new_dimensions[1])
        if new_dimensions[1] < height:
            new_dimensions = (new_dimensions[0], height)

        new_image = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_a = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_b = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        existing_image_pos = [0, 0]
        image_root_point = QPoint(root_point.x(), root_point.y())
        image_pivot_point = QPoint(pivot_point.x(), pivot_point.y())
        if is_drawing_left:
            current_x_pos = abs(outpaint_box_rect.x() - image_pivot_point.x())
            left_overlap = abs(outpaint_box_rect.x()) - abs(image_root_point.x())
            image_root_point.setX(width + left_overlap)
            image_pivot_point.setX(int(outpaint_box_rect.x()))
            existing_image_pos = [current_x_pos, existing_image_pos[1]]
            pos_x = max(0, outpaint_box_rect.x() - pivot_point.x())
        else:
            pos_x = max(0, outpaint_box_rect.x() - pivot_point.x())
        if is_drawing_up:
            current_y_pos = abs(outpaint_box_rect.y() - image_pivot_point.y())
            up_overlap = abs(outpaint_box_rect.y()) - abs(image_root_point.y())
            image_root_point.setY(height + up_overlap)
            image_pivot_point.setY(int(outpaint_box_rect.y()))
            existing_image_pos = [existing_image_pos[0], current_y_pos]
            pos_y = max(0, outpaint_box_rect.y() - pivot_point.y())
        else:
            pos_y = max(0, outpaint_box_rect.y() - pivot_point.y())

        # self.parent.canvas_widget.set_debug_text(
        #     outpaint_box_rect=outpaint_box_rect,
        #     image_pivot_point=pivot_point,
        #     image_root_point=root_point,
        #     is_drawing_left=is_drawing_left,
        #     is_drawing_right=is_drawing_right,
        #     is_drawing_up=is_drawing_up,
        #     is_drawing_down=is_drawing_down,
        #     x_overlap=x_overlap,
        #     y_overlap=y_overlap,
        #     new_dimensions=new_dimensions,
        #     current_image_position=current_image_position,
        #     image_dimensions=(width, height),
        #     pos=(int(pos_x), int(pos_y)),
        # )

        new_image_a.paste(outpainted_image, (int(pos_x), int(pos_y)))
        new_image_b.paste(existing_image_copy, (int(existing_image_pos[0]), int(existing_image_pos[1])))

        if action == "outpaint" and not is_kandinsky:
            new_image = Image.alpha_composite(new_image, new_image_a)
            new_image = Image.alpha_composite(new_image, new_image_b)
        else:
            new_image = Image.alpha_composite(new_image, new_image_b)
            new_image = Image.alpha_composite(new_image, new_image_a)

        return new_image, image_root_point, image_pivot_point

    def add_image_to_canvas(self, image, image_root_point, image_pivot_point, layer:LayerData=None):
        self.parent.history.add_event({
            "event": "set_image",
            "layer_index": self.current_layer_index,
            "images": self.current_layer.image_data
        })
        image = self.apply_opacity(image, self.current_layer.opacity)

        if not layer:
            layer = self.current_layer

        layer.image_data = ImageData(
            position=image_pivot_point,
            image=image,
            opacity=self.current_layer.opacity,
            image_root_point=image_root_point,
            image_pivot_point=image_pivot_point
        )
        # get layer widget from self.parent.tool_menu_widget.layer_container_widget.layers

        layer.layer_widget.set_thumbnail()
        self.update()

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
        return ImageData(
            position=image_data.position,
            image=image_data.image.copy() if image_data.image else None,
            opacity=self.current_layer.opacity,
            image_pivot_point=image_data.image_pivot_point,
            image_root_point=image_data.image_root_point
        )

    def rotate_90_clockwise(self):
        if self.current_active_image_data:
            if not self.current_active_image_data.image:
                return
            self.parent.history.add_event({
                "event": "rotate",
                "layer_index": self.current_layer_index,
                "images": self.image_data_copy(self.current_layer_index)
            })
            if self.current_active_image_data.image:
                self.current_active_image_data.image = self.current_active_image_data.image.transpose(Image.ROTATE_270)
            self.update()

    def rotate_90_counterclockwise(self):
        if self.current_active_image_data:
            if not self.current_active_image_data or not self.current_active_image_data.image:
                return
            self.parent.history.add_event({
                "event": "rotate",
                "layer_index": self.current_layer_index,
                "images": self.image_data_copy(self.current_layer_index)
            })
            if self.current_active_image_data.image:
                self.current_active_image_data.image = self.current_active_image_data.image.transpose(Image.ROTATE_90)
            self.update()
