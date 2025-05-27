import PIL
from PIL import ImageQt
from PIL.Image import Image
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainterPath
from PySide6.QtGui import QPen, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsLineItem

from airunner.data.models import DrawingPadSettings
from airunner.enums import SignalCode, CanvasToolName
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.gui.widgets.canvas.custom_scene import CustomScene
from airunner.gui.widgets.canvas.logic.brush_scene_logic import BrushSceneLogic
import logging


class BrushScene(CustomScene):
    settings_key = "drawing_pad_settings"

    def __init__(
        self,
        canvas_type: str,
        *,
        application_settings=None,
        _test_brush_settings=None,
        _test_drawing_pad_settings=None,
    ):
        super().__init__(canvas_type, application_settings=application_settings)
        self._test_brush_settings = _test_brush_settings
        self._test_drawing_pad_settings = _test_drawing_pad_settings
        # Only access these after parent __init__ has set up attributes
        if (
            hasattr(self, "application_settings")
            and self.application_settings is not None
        ):
            logic_args = (
                self.application_settings,
                getattr(self, "brush_settings", None),
                getattr(self, "drawing_pad_settings", None),
            )
        else:
            # For test cases where parent __init__ is patched out
            logic_args = (None, None, None)
        self._logic = BrushSceneLogic(*logic_args)
        brush_color = getattr(self, "brush_settings", None)
        if brush_color is not None:
            brush_color = self.brush_settings.primary_color
        else:
            brush_color = Qt.GlobalColor.black
        self._brush_color = QColor(brush_color)
        self.draw_button_down: bool = False
        pen_size = getattr(self, "brush_settings", None)
        if pen_size is not None:
            pen_size = self.brush_settings.size
        else:
            pen_size = 1
        self.pen = QPen(
            self._brush_color,
            pen_size,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        self.mask_item = None
        self.mask_image: ImageQt = None
        self.path = None
        self._is_drawing = False
        self._is_erasing = False
        self._do_generate_image = False

        self.register(
            SignalCode.BRUSH_COLOR_CHANGED_SIGNAL, self.on_brush_color_changed
        )

    @property
    def brush_settings(self):
        if self._test_brush_settings is not None:
            return self._test_brush_settings
        return super().brush_settings

    @property
    def drawing_pad_settings(self):
        if self._test_drawing_pad_settings is not None:
            return self._test_drawing_pad_settings
        return super().drawing_pad_settings

    @property
    def logic(self):
        return self._logic

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
        return (
            QColor(Qt.GlobalColor.white)
            if self.drawing_pad_settings.mask_layer_enabled
            else self._brush_color
        )

    @property
    def active_eraser_color(self):
        return (
            QColor(Qt.GlobalColor.black)
            if self.drawing_pad_settings.mask_layer_enabled
            else QColor(Qt.GlobalColor.transparent)
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

    def initialize_image(self, image: Image = None, generated: bool = False):
        super().initialize_image(image, generated=generated)
        self.stop_painter()
        self.set_mask()
        self.set_painter(
            self.mask_image
            if self.drawing_pad_settings.mask_layer_enabled
            else self.image
        )

    def drawBackground(self, painter, rect):
        if self.painter is None:
            self.refresh_image(self.current_active_image)
        if self.painter is not None and self.painter.isActive():
            if self.last_pos and self.draw_button_down:
                try:
                    item = self.active_item
                    if item is None:
                        return
                except RuntimeError:
                    return
                if self.current_tool is CanvasToolName.BRUSH:
                    self._draw_at(self.painter)
                elif self.current_tool is CanvasToolName.ERASER:
                    self._erase_at(self.painter)
        super().drawBackground(painter, rect)

    def rotate_image(self, angle: float):
        mask_updated = False
        mask = self.drawing_pad_settings.mask
        if mask is not None:
            mask = convert_binary_to_image(mask)
            mask = mask.rotate(angle, expand=True)
            self.update_drawing_pad_settings("mask", convert_image_to_binary(mask))
            mask_updated = True
        super().rotate_image(angle)
        if mask_updated:
            self.api.art.canvas.mask_updated()

    def _draw_at(self, painter=None):
        self._create_line(drawing=True, painter=painter, color=self.active_color)

    def _erase_at(self, painter=None):
        self._create_line(erasing=True, painter=painter, color=self.active_eraser_color)

    def _create_line(
        self,
        drawing: bool = False,
        erasing: bool = False,
        painter: QPainter = None,
        color: QColor = None,
    ):
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

        # Use scene coordinates minus image item position for image coordinates
        try:
            item = self.active_item
            if item is None:
                return
            item_pos = item.pos()
        except RuntimeError:
            # The C++ object has been deleted; abort drawing
            return
        image_start_pos = self.start_pos - item_pos
        image_last_pos = self.last_pos - item_pos

        # Move to start position in image coordinates
        self.path.moveTo(image_start_pos)

        # Create control point in image coordinates
        control_point = QPointF(
            (image_start_pos.x() + image_last_pos.x()) * 0.5,
            (image_start_pos.y() + image_last_pos.y()) * 0.5,
        )

        # Draw quadratic curve to end position in image coordinates
        self.path.quadTo(control_point, image_last_pos)

        # Draw the path
        painter.drawPath(self.path)

        # Update start position for next segment
        self.start_pos = self.last_pos

        # Create a QPixmap from the image and set it to the QGraphicsPixmapItem
        active_image = self.active_image

        pixmap = QPixmap.fromImage(active_image)

        # save the image - use updateImage if setPixmap is not available
        try:
            if hasattr(item, "setPixmap"):
                item.setPixmap(pixmap)
            elif hasattr(item, "updateImage"):
                item.updateImage(active_image)
        except RuntimeError:
            # Item was deleted during drawing, ignore
            return

    def create_line(self, event):
        scene_pt = event.scenePos()

        # Get canvas offset from parent view
        view = self.views()[0]
        canvas_offset = (
            view.canvas_offset if hasattr(view, "canvas_offset") else QPointF(0, 0)
        )

        # Apply canvas offset to convert scene coordinates to image coordinates
        x = scene_pt.x() + canvas_offset.x()
        y = scene_pt.y() + canvas_offset.y()

        new_line = QGraphicsLineItem(x, y, x + 10, y + 10)
        self.addItem(new_line)

    def _handle_left_mouse_press(self, event):
        # Use scenePos() so this matches the scene's offset
        self.draw_button_down = True
        self.start_pos = event.scenePos()
        if self.drawing_pad_settings.mask_layer_enabled and self.mask_image is None:
            self._create_mask_image()
        elif self.is_brush_or_eraser:
            self._add_image_to_undo()
        return super()._handle_left_mouse_press(event)

    def mouseMoveEvent(self, event):
        # Update last_pos with scenePos() for consistent drawing
        self.last_pos = event.scenePos()
        super().mouseMoveEvent(event)

    def _handle_left_mouse_release(self, event) -> bool:
        self.draw_button_down = False
        drawing_pad_settings = DrawingPadSettings.objects.first()

        # First get the correct image
        if self.drawing_pad_settings.mask_layer_enabled:
            # For mask layer
            mask_image: Image = ImageQt.fromqimage(self.mask_image)
            # Ensure mask is fully opaque
            mask_image = mask_image.convert("L").point(lambda p: 255 if p > 128 else 0)
            base_64_image = convert_image_to_binary(mask_image)
            # Update both database object and in-memory settings with the same base64 image
            drawing_pad_settings.mask = base_64_image
            self.update_drawing_pad_settings("mask", base_64_image)
        else:
            # For normal image layer
            if self.active_image is not None:
                image = ImageQt.fromqimage(self.active_image)
                base_64_image = convert_image_to_binary(image)
                # Update both database object and in-memory settings with the same base64 image
                drawing_pad_settings.image = base_64_image
                self.update_drawing_pad_settings("image", base_64_image)

                if self.current_tool and (
                    self.current_tool is CanvasToolName.BRUSH
                    or self.current_tool is CanvasToolName.ERASER
                ):
                    self.api.art.canvas.generate_mask()

        # Ensure changes are saved to database only for real model instances
        if (
            hasattr(drawing_pad_settings, "save")
            and callable(drawing_pad_settings.save)
            and not type(drawing_pad_settings).__name__.endswith("Data")
        ):
            drawing_pad_settings.save()
        # else: do not log anything for dataclasses

        # Emit signals to refresh related UI
        self.api.art.canvas.image_updated()
        if self.drawing_pad_settings.mask_layer_enabled:
            self.initialize_image()
            self.api.art.canvas.mask_updated()

    def set_mask(self):
        mask = None
        if self.drawing_pad_settings.mask_layer_enabled:
            mask = self.drawing_pad_settings.mask
            if mask is not None:
                mask = convert_binary_to_image(mask)
        if mask is not None:
            mask = self.logic.adjust_mask_alpha(mask)
            q_mask = ImageQt.ImageQt(mask)
            self.mask_image = q_mask
            if self.mask_item is None:
                self.mask_item = QGraphicsPixmapItem(QPixmap.fromImage(q_mask))
                self.mask_item.setZValue(2)
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
        mask_image = self.logic.create_mask_image()
        self.update_drawing_pad_settings("mask", convert_image_to_binary(mask_image))
        self.mask_image = ImageQt.ImageQt(mask_image)
        self.initialize_image()
        self.api.art.canvas.mask_updated()
