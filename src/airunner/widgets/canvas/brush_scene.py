from PIL import ImageQt, Image
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainterPath
from PySide6.QtGui import QPen, QPixmap, QPainter
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFileDialog
from airunner.enums import SignalCode, CanvasToolName
from airunner.settings import VALID_IMAGE_FILES
from airunner.utils.convert_image_to_base64 import convert_image_to_base64
from airunner.widgets.canvas.custom_scene import CustomScene


class BrushScene(CustomScene):
    settings_key = "drawing_pad_settings"

    def __init__(self, canvas_type: str):
        super().__init__(canvas_type)
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
        self._do_generate_image = False

    @property
    def is_brush_or_eraser(self):
        return self.settings["current_tool"] in (
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER
        )

    def register_signals(self):
        signals = [
            (SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_clockwise_signal),
            (SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_counter_clockwise_signal),
            (SignalCode.CANVAS_PASTE_IMAGE_SIGNAL, self.on_paste_image_from_clipboard),
            (SignalCode.BRUSH_COPY_IMAGE_SIGNAL, self.on_canvas_copy_image_signal),
            (SignalCode.BRUSH_CUT_IMAGE_SIGNAL, self.on_canvas_cut_image_signal),
            (SignalCode.BRUSH_PASTE_IMAGE_SIGNAL, self.on_paste_image_from_clipboard),
            (SignalCode.BRUSH_EXPORT_IMAGE_SIGNAL, self.export_image),
            (SignalCode.BRUSH_IMPORT_IMAGE_SIGNAL, self.import_image),
            (SignalCode.BRUSH_COLOR_CHANGED_SIGNAL, self.handle_brush_color_changed),
            (SignalCode.DRAWINGPAD_IMPORT_IMAGE_SIGNAL, self.import_image),
            (SignalCode.DRAWINGPAD_EXPORT_IMAGE_SIGNAL, self.export_image),
            (SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.handle_settings_changed)
        ]
        for signal, handler in signals:
            self.register(signal, handler)
        super().register_signals()

    def export_image(self):
        image = self.current_active_image()
        if image:
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Save Image",
                "",
                f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
            )
            if file_path == "":
                return

            # If missing file extension, add it
            if not file_path.endswith(VALID_IMAGE_FILES):
                file_path = f"{file_path}.png"

            image.save(file_path)

    def import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            "",
            f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
        )
        if file_path == "":
            return
        self.load_image(file_path)

    def handle_brush_color_changed(self, data):
        self._brush_color = QColor(data["color"])

    def drawBackground(self, painter, rect):
        if self.painter is None:
            self.refresh_image()

        if self.painter is not None and self.painter.isActive():
            self.painter.drawImage(0, 0, self.image)

            if self.last_pos:
                settings = self.settings
                if settings["current_tool"] is CanvasToolName.BRUSH:
                    self.draw_at(self.painter)
                elif settings["current_tool"] is CanvasToolName.ERASER:
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
        if self.scene_is_active and event.button() == Qt.MouseButton.LeftButton:
            self.handle_left_mouse_press(event)
            self.handle_cursor(event)
            if not self.is_brush_or_eraser:
                super().mousePressEvent(event)
            elif self.settings["drawing_pad_settings"]["enable_automatic_drawing"]:
                self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.scene_is_active and event.button() == Qt.MouseButton.LeftButton:
            self._is_drawing = False
            self._is_erasing = False
            self.last_pos = None
            self.start_pos = None
            if type(self.image) is Image:
                image = ImageQt.ImageQt(self.image.convert("RGBA"))
            else:
                image = self.image
            pil_image = ImageQt.fromqimage(image)
            self._do_generate_image = True
            settings = self.settings
            settings[self.settings_key]["image"] = convert_image_to_base64(pil_image)
            self.settings = settings
            self.do_update = False

    def handle_settings_changed(self):
        if self._do_generate_image:
            self._do_generate_image = False
            if (
                self.settings["drawing_pad_settings"]["enable_automatic_drawing"] and
                (
                    self.settings["current_tool"] is CanvasToolName.BRUSH or
                    self.settings["current_tool"] is CanvasToolName.ERASER
                )
            ):
                self.emit_signal(SignalCode.DO_GENERATE_SIGNAL)

    def mouseMoveEvent(self, event):
        if self.scene_is_active:
            self.last_pos = event.scenePos()
            self.update()
