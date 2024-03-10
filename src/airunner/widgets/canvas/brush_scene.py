from PIL import ImageQt, Image
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainterPath
from PyQt6.QtGui import QPen, QPixmap, QPainter
from PyQt6.QtGui import QColor
from airunner.enums import SignalCode, CanvasToolName
from airunner.utils import convert_image_to_base64, create_worker
from airunner.widgets.canvas.custom_scene import CustomScene
from airunner.workers.update_scene_worker import UpdateSceneWorker


class BrushScene(CustomScene):
    settings_key = "drawing_pad_settings"

    def __init__(self, size):
        super().__init__(size)
        brush_settings = self.settings["brush_settings"]
        brush_color = brush_settings["primary_color"]
        self._brush_color = QColor(brush_color)
        self.pen = QPen(
            self._brush_color,
            brush_settings["size"],
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap
        )
        self.path = None
        self._is_drawing = False
        self._is_erasing = False
        self.register(
            SignalCode.BRUSH_COLOR_CHANGED_SIGNAL,
            self.handle_brush_color_changed
        )
        self.update_scene_worker = create_worker(UpdateSceneWorker)
        self.update_scene_worker.scene = self

    def register_signals(self):
        pass

    @property
    def is_brush_or_eraser(self):
        return self.settings["current_tool"] in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER
        )

    def handle_brush_color_changed(self, color_name):
        self._brush_color = QColor(color_name)

    def drawBackground(self, painter, rect):
        if self.painter is None:
            self.refresh_image()

        if self.painter is not None and self.painter.isActive():
            self.painter.drawImage(0, 0, self.image)

            if self.last_pos:
                if self.settings["current_tool"] is CanvasToolName.BRUSH:
                    self.draw_at(self.painter)
                elif self.settings["current_tool"] is CanvasToolName.ERASER:
                    self.erase_at(self.painter)
        super().drawBackground(painter, rect)

    def create_line(self, drawing=False, erasing=False, painter=None, color: QColor=None):
        if drawing and not self._is_drawing or erasing and not self._is_erasing:
            self._is_drawing = drawing
            self._is_erasing = erasing

            # set the size of the pen
            self.pen.setWidth(self.settings["brush_settings"]["size"])

            if drawing:
                composition_mode = QPainter.CompositionMode.CompositionMode_SourceOver
            else:
                composition_mode = QPainter.CompositionMode.CompositionMode_Source

            # check if painter is active
            if not painter.isActive():
                painter.begin(self.image)

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
        pixmap = QPixmap.fromImage(self.image)

        # save the image
        self.item.setPixmap(pixmap)

    def draw_at(self, painter=None):
        self.create_line(
            drawing=True,
            painter=painter
        )

    def erase_at(self, painter=None):
        self.create_line(
            erasing=True,
            painter=painter,
            color=QColor(Qt.GlobalColor.transparent)
        )

    def handle_mouse_event(self, event, is_press_event):
        pass

    def mousePressEvent(self, event):
        self.handle_left_mouse_press(event)
        self.handle_cursor(event)
        if not self.is_brush_or_eraser:
            super().mousePressEvent(event)
        elif self.settings["canvas_settings"]["enable_automatic_drawing"]:
            self.emit(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._is_drawing = False
        self._is_erasing = False
        self.last_pos = None
        self.start_pos = None
        if type(self.image) is Image:
            image = ImageQt.ImageQt(self.image.convert("RGBA"))
        else:
            image = self.image
        pil_image = ImageQt.fromqimage(image)
        settings = self.settings
        settings[self.settings_key]["image"] = convert_image_to_base64(pil_image)
        self.settings = settings
        self.do_update = False
        if self.settings["canvas_settings"]["enable_automatic_drawing"]:
            self.emit(SignalCode.DO_GENERATE_SIGNAL)

    def mouseMoveEvent(self, event):
        self.last_pos = event.scenePos()
