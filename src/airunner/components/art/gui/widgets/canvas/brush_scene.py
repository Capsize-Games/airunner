import PIL
from typing import Optional
from PIL import ImageQt
from PIL.Image import Image
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QPixmap, QPainter, QColor, QPainterPath
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsLineItem

from airunner.enums import SignalCode, CanvasToolName
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.components.art.gui.widgets.canvas.custom_scene import CustomScene


class BrushScene(CustomScene):
    settings_key = "drawing_pad_settings"

    def __init__(self, canvas_type: str):
        super().__init__(canvas_type)
        brush_color = self.brush_settings.primary_color
        self._brush_color = QColor(brush_color)
        self.draw_button_down: bool = False
        self.pen = QPen(
            self._brush_color,
            self.brush_settings.size,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        self.mask_item = None
        self.mask_image: ImageQt = None
        self.path = None
        self._is_drawing = False
        self._is_erasing = False
        self._do_generate_image = False
        self._pending_brush_history_layer: Optional[int] = None
        self.register(
            SignalCode.BRUSH_COLOR_CHANGED_SIGNAL, self.on_brush_color_changed
        )
        self.register(
            SignalCode.LAYER_SELECTION_CHANGED, self.on_layer_selection_changed
        )

    @property
    def active_image(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return self.mask_image
        layer_item = self._get_active_layer_item()
        if layer_item is not None and getattr(layer_item, "qimage", None):
            return layer_item.qimage
        return self.image

    @property
    def active_item(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return self.mask_item
        layer_item = self._get_active_layer_item()
        if layer_item is not None:
            return layer_item
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

    def on_brush_color_changed(self, data):
        self._brush_color = QColor(data["color"])

    def on_layer_selection_changed(self, data):
        """Handle layer selection changes to update painter target."""
        self.stop_painter()
        self._rebind_active_painter()

    def on_layers_show_signal(self, data=None):
        super().on_layers_show_signal(data)
        self.stop_painter()
        self._rebind_active_painter()

    def on_canvas_clear_signal(self):
        self.update_drawing_pad_settings(mask=None)
        super().on_canvas_clear_signal()

    def delete_image(self):
        # Remove mask item if present
        item_scene = None
        if self.mask_item is not None:
            item_scene = self.mask_item.scene()
        if item_scene is not None:
            item_scene.removeItem(self.mask_item)

        # Ensure any painter is stopped and reset
        if self.painter and self.painter.isActive():
            self.painter.end()
        self.painter = None

        # Clear mask image reference; don't recreate yet
        self.mask_image = None

        # Let base class remove the main image item and reset state
        super().delete_image()

    def initialize_image(self, image: Image = None, generated: bool = False):
        super().initialize_image(image, generated=generated)
        self.stop_painter()
        self.set_mask()
        self._rebind_active_painter()

    def drawBackground(self, painter, rect):
        if self.painter is None:
            # Attempt to bind to the current active image target first
            self._rebind_active_painter()
            if self.painter is None:
                image = self._current_active_image_ref
                if image is None:
                    image = self.current_active_image
                self.refresh_image(image)
        if self.painter is not None and self.painter.isActive():
            if self.last_pos and self.draw_button_down:
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
            self.update_drawing_pad_settings(
                mask=convert_image_to_binary(mask)
            )
            mask_updated = True
        super().rotate_image(angle)
        if mask_updated:
            self.api.art.canvas.mask_updated()

    def _draw_at(self, painter=None):
        self._create_line(
            drawing=True, painter=painter, color=self.active_color
        )

    def _erase_at(self, painter=None):
        self._create_line(
            erasing=True, painter=painter, color=self.active_eraser_color
        )

    def _rebind_active_painter(self):
        target_image = None
        if self.drawing_pad_settings.mask_layer_enabled:
            target_image = self.mask_image
        else:
            layer_item = self._get_active_layer_item()
            if layer_item and getattr(layer_item, "qimage", None):
                target_image = layer_item.qimage
            elif self.image is not None:
                target_image = self.image

        if target_image is not None:
            self.set_painter(target_image)
        else:
            self.stop_painter()

    def _create_line(
        self,
        drawing: bool = False,
        erasing: bool = False,
        painter: QPainter = None,
        color: QColor = None,
    ):
        ensure_start = ensure_last = False
        if not self.drawing_pad_settings.mask_layer_enabled:
            if self.start_pos is not None:
                ensure_start = self._ensure_draw_space(self.start_pos)
            if self.last_pos is not None:
                ensure_last = self._ensure_draw_space(self.last_pos)

        needs_pen_setup = painter is None

        if ensure_start or ensure_last or painter is None:
            previous_target = self._painter_target
            self._rebind_active_painter()
            painter = self.painter
            if painter is None:
                return
            needs_pen_setup = True
            if ensure_start or ensure_last:
                self.path = None

        new_stroke = False
        if drawing and not self._is_drawing:
            self._is_drawing = True
            self._is_erasing = False
            new_stroke = True
        elif erasing and not self._is_erasing:
            self._is_erasing = True
            self._is_drawing = False
            new_stroke = True

        pen_color = self._brush_color if color is None else color
        pen_width = max(1, int(self.brush_settings.size))

        if new_stroke or self.path is None or needs_pen_setup:
            self.pen = QPen(
                pen_color,
                pen_width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        else:
            self.pen.setColor(pen_color)
            if self.pen.width() != pen_width:
                self.pen.setWidth(pen_width)

        painter.setPen(self.pen)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Source
        )

        if self.drawing_pad_settings.mask_layer_enabled:
            painter.setOpacity(0.5 if drawing else 0)
        else:
            painter.setOpacity(1.0)

        if new_stroke or self.path is None:
            self.path = QPainterPath()

        if not self.start_pos:
            return

        # Use scene coordinates minus image item position for image coordinates
        item_pos = (
            self.active_item.pos() if self.active_item else QPointF(0, 0)
        )
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
        if hasattr(self.active_item, "setPixmap"):
            self.active_item.setPixmap(pixmap)
        elif hasattr(self.active_item, "updateImage"):
            self.active_item.updateImage(active_image)

    def _ensure_draw_space(self, scene_point: QPointF) -> bool:
        if scene_point is None:
            return False
        if self.drawing_pad_settings.mask_layer_enabled:
            return False
        item = self._get_active_layer_item()
        if item is None and self.item is not None:
            item = self.item
        if item is None:
            return False
        radius = (self.brush_settings.size or 1) * 0.5 + 8
        return self._ensure_item_contains_scene_point(
            item, scene_point, radius
        )

    def create_line(self, event):
        scene_pt = event.scenePos()

        # Get canvas offset from parent view
        view = self.views()[0]
        canvas_offset = (
            view.canvas_offset
            if hasattr(view, "canvas_offset")
            else QPointF(0, 0)
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
        if self._ensure_draw_space(self.start_pos):
            self._rebind_active_painter()
        if (
            self.drawing_pad_settings.mask_layer_enabled
            and self.mask_image is None
        ):
            self._create_mask_image()
        if self.is_brush_or_eraser:
            self._pending_brush_history_layer = self._add_image_to_undo()
        self._rebind_active_painter()
        return super()._handle_left_mouse_press(event)

    def mouseMoveEvent(self, event):
        # Update last_pos with scenePos() for consistent drawing
        self.last_pos = event.scenePos()
        if self._ensure_draw_space(self.last_pos):
            self._rebind_active_painter()
        super().mouseMoveEvent(event)

    def _handle_left_mouse_release(self, event) -> bool:
        self.draw_button_down = False

        # First get the correct image
        if self.drawing_pad_settings.mask_layer_enabled:
            # For mask layer
            mask_image: Image = ImageQt.fromqimage(self.mask_image)
            # Ensure mask is fully opaque
            mask_image = mask_image.convert("L").point(
                lambda p: 255 if p > 128 else 0
            )
            base_64_image = convert_image_to_binary(mask_image)
            # Update both database object and in-memory settings with the same base64 image
            self.update_drawing_pad_settings(mask=base_64_image)
        else:
            # For normal image layer
            if self.active_image is not None:
                image = ImageQt.fromqimage(self.active_image)
                base_64_image = convert_image_to_binary(image)
                # Update both database object and in-memory settings with the same base64 image
                self.update_drawing_pad_settings(image=base_64_image)

                # CRITICAL: Update the cached reference to ensure consistency
                self._current_active_image_ref = image
                self._current_active_image_binary = base_64_image

                if self.current_tool and (
                    self.current_tool is CanvasToolName.BRUSH
                    or self.current_tool is CanvasToolName.ERASER
                ):
                    self.api.art.canvas.generate_mask()

        # Emit signals to refresh related UI
        self.api.art.canvas.image_updated()
        if self.drawing_pad_settings.mask_layer_enabled:
            self.initialize_image()
            self.api.art.canvas.mask_updated()

        if self._pending_brush_history_layer is not None:
            self._commit_layer_history_transaction(
                self._pending_brush_history_layer, "image"
            )
            self._pending_brush_history_layer = None

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
            def adjust_alpha(red, green, blue, alpha):
                if red == 0 and green == 0 and blue == 0:
                    return 0
                elif red == 255 and green == 255 and blue == 255:
                    return 128
                else:
                    return alpha

            # Apply the adjust_alpha function to each pixel
            new_alpha = [
                adjust_alpha(
                    r.getpixel((x, y)),
                    g.getpixel((x, y)),
                    b.getpixel((x, y)),
                    alpha.getpixel((x, y)),
                )
                for y in range(mask.height)
                for x in range(mask.width)
            ]
            alpha.putdata(new_alpha)
            mask.putalpha(alpha)

            q_mask = ImageQt.ImageQt(mask)
            self.mask_image = q_mask
            if self.mask_item is None:
                self.mask_item = QGraphicsPixmapItem(QPixmap.fromImage(q_mask))
                self.mask_item.setZValue(
                    2
                )  # Ensure the mask is above the image
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
        mask_image = PIL.Image.new(
            "RGBA",
            (
                self.application_settings.working_width,
                self.application_settings.working_height,
            ),
            (0, 0, 0, 255),
        )
        self.update_drawing_pad_settings(
            mask=convert_image_to_binary(mask_image)
        )
        self.mask_image = ImageQt.ImageQt(mask_image)
        self.initialize_image()
        self.api.art.canvas.mask_updated()
