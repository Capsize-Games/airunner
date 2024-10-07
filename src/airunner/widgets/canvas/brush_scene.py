from PIL import ImageQt
from PIL.Image import Image
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainterPath
from PySide6.QtGui import QPen, QPixmap, QPainter
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFileDialog

from airunner.aihandler.models.settings_models import DrawingPadSettings
from airunner.enums import SignalCode, CanvasToolName
from airunner.settings import VALID_IMAGE_FILES
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.utils.convert_image_to_base64 import convert_image_to_base64
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
        self.path = None
        self._is_drawing = False
        self._is_erasing = False
        self._do_generate_image = False

        self.register(SignalCode.BRUSH_COLOR_CHANGED_SIGNAL, self.handle_brush_color_changed)

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

    def handle_brush_color_changed(self, data):
        self._brush_color = QColor(data["color"])

    def drawBackground(self, painter, rect):
        if self.painter is None:
            self.refresh_image()
        if self.painter is not None and self.painter.isActive():
            self.painter.drawImage(0, 0, self.active_image)

            if self.last_pos:
                if self.current_tool is CanvasToolName.BRUSH:
                    self.draw_at(self.painter)
                elif self.current_tool is CanvasToolName.ERASER:
                    self.erase_at(self.painter)
        super().drawBackground(painter, rect)

    def create_line(self, drawing=False, erasing=False, painter=None, color: QColor=None):
        if drawing and not self._is_drawing or erasing and not self._is_erasing:
            self._is_drawing = drawing
            self._is_erasing = erasing

            # set the size of the pen
            self.pen.setWidth(self.brush_settings.size)

            if drawing:
                composition_mode = QPainter.CompositionMode.CompositionMode_SourceOver
            else:
                composition_mode = QPainter.CompositionMode.CompositionMode_Source

            # check if painter is active
            if not painter.isActive():
                painter.begin(self.active_image)

            self.pen.setColor(self._brush_color if color is None else color)

            # Set the pen to the painter
            painter.setPen(self.pen)

            # Set the CompositionMode to SourceOver
            painter.setCompositionMode(composition_mode)

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

        if self.drawing_pad_settings.mask_layer_enabled:
            pil_image = ImageQt.fromqimage(active_image)
            pil_image = pil_image.convert("RGBA")
            alpha = pil_image.split()[3]
            alpha = alpha.point(lambda p: p * 0.5)
            pil_image.putalpha(alpha)
            active_image = ImageQt.ImageQt(pil_image)

        pixmap = QPixmap.fromImage(active_image)

        # save the image
        self.active_item.setPixmap(pixmap)

    def draw_at(self, painter=None):
        self.create_line(
            drawing=True,
            painter=painter,
            color=self.active_color
        )

    def erase_at(self, painter=None):
        self.create_line(
            erasing=True,
            painter=painter,
            color=self.active_eraser_color
        )

    def convert_imageqt_to_base64(self, imageqt: ImageQt) -> str:
        image = ImageQt.fromqimage(imageqt)
        return convert_image_to_base64(image)

    def handle_left_mouse_release(self, event) -> bool:
        if self.drawing_pad_settings.mask_layer_enabled:
            mask_image: Image = ImageQt.fromqimage(self.mask_image)
            base_64_image = convert_image_to_base64(mask_image)
            session = self.db_handler.get_db_session()
            drawing_pad_settings = session.query(DrawingPadSettings).first()
            drawing_pad_settings.mask = base_64_image
            session.commit()
            session.close()
            self.emit_signal(SignalCode.MASK_UPDATED)
        else:
            base_64_image = self.convert_imageqt_to_base64(self.active_image)
            self.update_drawing_pad_settings("image", base_64_image)
            if ((
                self.current_tool is CanvasToolName.BRUSH or
                self.current_tool is CanvasToolName.ERASER
            )):
                self.emit_signal(SignalCode.GENERATE_MASK)
        return super().handle_left_mouse_release(event)
