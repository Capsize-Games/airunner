import PIL
from PIL import ImageQt
from PIL.Image import Image
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainterPath
from PySide6.QtGui import QPen, QPixmap, QPainter
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsPixmapItem

from airunner.data.models import DrawingPadSettings
from airunner.enums import SignalCode, CanvasToolName
from airunner.utils.image.convert_binary_to_image import convert_binary_to_image
from airunner.utils.image.convert_image_to_binary import convert_image_to_binary
from airunner.widgets.canvas.custom_scene import CustomScene


class BrushScene(CustomScene):
    settings_key = "drawing_pad_settings"

    def __init__(self, canvas_type: str):
        super().__init__(canvas_type)
        brush_color = self.brush_settings.primary_color
        self._brush_color = QColor(brush_color)
        self.pen = QPen(
            self._brush_color,
            self.brush_settings.size,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap
        )
        self.mask_item = None
        self.mask_image: ImageQt = None
        self.path = None
        self._is_drawing = False
        self._is_erasing = False
        self._do_generate_image = False

        self.register(SignalCode.BRUSH_COLOR_CHANGED_SIGNAL, self.on_brush_color_changed)

    @property
    def active_image(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return self.mask_image
        return self.image

    @property
    def active_item(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return self.mask_item
        return self.item

    @property
    def active_color(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return QColor(Qt.GlobalColor.white)
        return self._brush_color

    @property
    def active_eraser_color(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return QColor(Qt.GlobalColor.black)
        return QColor(Qt.GlobalColor.transparent)

    @property
    def is_brush_or_eraser(self):
        return self.current_tool in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER
        )

    def on_brush_color_changed(self, data):
        self._brush_color = QColor(data["color"])

    def on_canvas_clear_signal(self):
        self.update_drawing_pad_settings("mask", None)
        super().on_canvas_clear_signal()

    def delete_image(self):
        item_scene = None
        if self.mask_item is not None:
            item_scene = self.mask_item.scene()
        if item_scene is not None:
            item_scene.removeItem(self.mask_item)
        if self.painter and self.painter.isActive():
            self.painter.end()
        self.mask_image = None
        self._create_mask_image()
        super().delete_image()

    def initialize_image(self, image: Image = None):
        super().initialize_image(image)
        self.stop_painter()
        self.set_mask()
        self.set_painter(self.mask_image if self.drawing_pad_settings.mask_layer_enabled else self.image)

    def drawBackground(self, painter, rect):
        if self.painter is None:
            self.refresh_image(self.current_active_image)
        if self.painter is not None and self.painter.isActive():
            #self.painter.drawImage(0, 0, self.active_image)

            if self.last_pos:
                if self.current_tool is CanvasToolName.BRUSH:
                    self._draw_at(self.painter)
                elif self.current_tool is CanvasToolName.ERASER:
                    self._erase_at(self.painter)
        super().drawBackground(painter, rect)

    def rotate_image(
        self,
        angle: float
    ):
        mask_updated = False
        mask = self.drawing_pad_settings.mask
        if mask is not None:
            mask = convert_binary_to_image(mask)
            mask = mask.rotate(angle, expand=True)
            self.update_drawing_pad_settings("mask", convert_image_to_binary(mask))
            mask_updated = True
        super().rotate_image(angle)
        if mask_updated:
            self.emit_signal(SignalCode.MASK_UPDATED)

    def _draw_at(self, painter=None):
        self._create_line(
            drawing=True,
            painter=painter,
            color=self.active_color
        )

    def _erase_at(self, painter=None):
        self._create_line(
            erasing=True,
            painter=painter,
            color=self.active_eraser_color
        )

    def _create_line(self, drawing=False, erasing=False, painter=None, color: QColor=None):
        if (drawing and not self._is_drawing) or (erasing and not self._is_erasing):
            self._is_drawing = drawing
            self._is_erasing = erasing

            # set the size of the pen
            self.pen.setWidth(self.brush_settings.size)

            composition_mode = QPainter.CompositionMode.CompositionMode_Source

            self.pen.setColor(self._brush_color if color is None else color)

            # Set the pen to the painter
            painter.setPen(self.pen)

            # Set the CompositionMode to SourceOver
            painter.setCompositionMode(composition_mode)

            # Set pen opacity to 50%
            if self.drawing_pad_settings.mask_layer_enabled:
                painter.setOpacity(0.5 if drawing else 0)

            # Create a QPainterPath object
            self.path = QPainterPath()

        if not self.start_pos:
            return

        self.path.moveTo(self.start_pos)

        # Calculate the midpoint and use it as control point for quadTo
        start_pos = self.start_pos
        last_pos = self.last_pos

        control_point = QPointF(
            (start_pos.x() + last_pos.x()) * 0.5,
            (start_pos.y() + last_pos.y()) * 0.5
        )
        self.path.quadTo(
            control_point,
            self.last_pos
        )

        # Draw the path
        painter.drawPath(self.path)

        self.start_pos = self.last_pos

        # Create a QPixmap from the image and set it to the QGraphicsPixmapItem
        active_image = self.active_image

        pixmap = QPixmap.fromImage(active_image)

        # save the image
        self.active_item.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if self.drawing_pad_settings.mask_layer_enabled and self.mask_image is None:
            self._create_mask_image()
        elif self.is_brush_or_eraser:
            self._add_image_to_undo()
        return super().mousePressEvent(event)

    def _handle_left_mouse_release(self, event) -> bool:
        drawing_pad_settings = DrawingPadSettings.objects.first()
        if self.drawing_pad_settings.mask_layer_enabled:
            mask_image: Image = ImageQt.fromqimage(self.mask_image)
            # Ensure mask is fully opaque
            mask_image = mask_image.convert("L").point(lambda p: 255 if p > 128 else 0)
            base_64_image = convert_image_to_binary(mask_image)
            drawing_pad_settings.mask = base_64_image
        else:
            image = ImageQt.fromqimage(self.active_image)
            base_64_image = convert_image_to_binary(image)
            drawing_pad_settings.image = base_64_image
            if ((
                self.current_tool is CanvasToolName.BRUSH or
                self.current_tool is CanvasToolName.ERASER
            )):
                self.emit_signal(SignalCode.GENERATE_MASK)
        drawing_pad_settings.save()
        
        self.emit_signal(SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL)
        if self.drawing_pad_settings.mask_layer_enabled:
            self.initialize_image()
            self.emit_signal(SignalCode.MASK_UPDATED)
        return super()._handle_left_mouse_release(event)

    def set_mask(self):
        mask = None
        if self.drawing_pad_settings.mask_layer_enabled:
            mask = self.drawing_pad_settings.mask
            if mask is not None:
                mask = convert_binary_to_image(mask)
        if mask is not None:
            # Convert the mask to RGBA
            mask = mask.convert("RGBA")
            r, g, b, alpha = mask.split()

            # Make black areas fully transparent and white areas 50% transparent
            def adjust_alpha(r, g, b, a):
                if r == 0 and g == 0 and b == 0:
                    return 0
                elif r == 255 and g == 255 and b == 255:
                    return 128
                else:
                    return a

            # Apply the adjust_alpha function to each pixel
            new_alpha = [
                adjust_alpha(r.getpixel((x, y)), g.getpixel((x, y)), b.getpixel((x, y)), alpha.getpixel((x, y))) for y
                in range(mask.height) for x in range(mask.width)]
            alpha.putdata(new_alpha)
            mask.putalpha(alpha)

            q_mask = ImageQt.ImageQt(mask)
            self.mask_image = q_mask
            if self.mask_item is None:
                self.mask_item = QGraphicsPixmapItem(QPixmap.fromImage(q_mask))
                self.mask_item.setZValue(2)  # Ensure the mask is above the image
                self.addItem(self.mask_item)
            else:
                self.mask_item.setPixmap(QPixmap.fromImage(q_mask))
                if self.mask_item.scene() is None:
                    self.addItem(self.mask_item)
        else:
            if self.mask_item is not None:
                self.removeItem(self.mask_item)
                self.mask_item = None

    def _create_mask_image(self):
        mask_image = PIL.Image.new("RGBA", (self.active_grid_settings.width, self.active_grid_settings.height), (0, 0, 0, 255))
        self.update_drawing_pad_settings("mask", convert_image_to_binary(mask_image))
        self.mask_image = ImageQt.ImageQt(mask_image)
        self.initialize_image()
        self.emit_signal(SignalCode.MASK_UPDATED)
