import PIL
from typing import Optional
from PIL import ImageQt
from PIL.Image import Image
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QImage,
    QPen,
    QPixmap,
    QPainter,
    QColor,
    QPainterPath,
)
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsLineItem

from airunner.enums import SignalCode, CanvasToolName
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.components.art.gui.widgets.canvas.custom_scene import CustomScene
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class BrushScene(CustomScene):
    settings_key = "drawing_pad_settings"

    def __init__(self, canvas_type: str):
        self.signal_handlers = {
            SignalCode.BRUSH_COLOR_CHANGED_SIGNAL: self.on_brush_color_changed,
            SignalCode.LAYER_SELECTION_CHANGED: self.on_layer_selection_changed,
        }
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
        self._is_drawing = False
        self._is_erasing = False
        self._do_generate_image = False
        self._pending_brush_history_layer: Optional[int] = None
        self._last_draw_scene_pos: Optional[QPointF] = None
        self._stroke_base_image: Optional[QImage] = None
        self._stroke_buffer_image: Optional[QImage] = None
        self._stroke_buffer_erasing = False
        self._stroke_item: Optional[QGraphicsPixmapItem] = None
        self._stroke_target_item = None
        self._stroke_target_layer_id: Optional[int] = None

    @property
    def active_image(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return self.mask_image
        layer_item = BrushScene._resolve_layer_canvas_item(self)
        if layer_item is not None and getattr(layer_item, "qimage", None):
            return layer_item.qimage
        if BrushScene._scene_uses_layer_canvas(self):
            return None
        return self.image

    @property
    def active_item(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return self.mask_item
        layer_item = BrushScene._resolve_layer_canvas_item(self)
        if layer_item is not None:
            return layer_item
        if BrushScene._scene_uses_layer_canvas(self):
            return None
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

    def _scene_uses_layer_canvas(self) -> bool:
        uses_layer_canvas = getattr(type(self), "_uses_layer_canvas", None)
        if uses_layer_canvas is not None:
            return uses_layer_canvas(self)

        uses_layer_canvas = getattr(
            getattr(self, "__dict__", {}),
            "get",
            lambda *_args, **_kwargs: None,
        )("_uses_layer_canvas")
        if callable(uses_layer_canvas):
            return uses_layer_canvas()

        canvas_type = getattr(self, "canvas_type", None)
        return canvas_type in ("drawing_pad", "brush")

    def _resolve_layer_canvas_item(self):
        resolve_layer_item = getattr(type(self), "_get_layer_canvas_item", None)
        if resolve_layer_item is not None:
            return resolve_layer_item(self)

        resolve_layer_item = getattr(
            getattr(self, "__dict__", {}),
            "get",
            lambda *_args, **_kwargs: None,
        )("_get_layer_canvas_item")
        if callable(resolve_layer_item):
            return resolve_layer_item()

        get_active_item = getattr(self, "_get_active_layer_item", None)
        if callable(get_active_item):
            layer_item = get_active_item()
            if layer_item is not None:
                return layer_item

        layer_items = getattr(self, "_layer_items", None)
        if not isinstance(layer_items, dict):
            return None
        for layer_id in sorted(layer_items):
            layer_item = layer_items.get(layer_id)
            if layer_item is not None:
                return layer_item
        return None

    def on_brush_color_changed(self, data):
        self._brush_color = QColor(data["color"])

    def on_layer_selection_changed(self, data):
        """Handle layer selection changes to update painter target."""
        if self.draw_button_down and self._stroke_target_item is not None:
            return
        self._clear_stroke_buffer()
        self.stop_painter()
        self._rebind_active_painter()

    def on_layers_show_signal(self, data=None):
        self._clear_stroke_buffer()
        super().on_layers_show_signal(data)
        self.stop_painter()
        self._rebind_active_painter()

    def on_canvas_clear_signal(self):
        self._clear_stroke_buffer()
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
        self._clear_stroke_buffer()

        # Let base class remove the main image item and reset state
        super().delete_image()

    def initialize_image(self, image: Image = None, generated: bool = False):
        self._clear_stroke_buffer()
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

    def _clear_stroke_buffer(self) -> None:
        self._remove_stroke_item()
        self._stroke_target_item = None
        self._stroke_target_layer_id = None
        self._stroke_base_image = None
        self._stroke_buffer_image = None
        self._stroke_buffer_erasing = False

    def _remove_stroke_item(self) -> None:
        if self._stroke_item is None:
            return
        try:
            if self._stroke_item.scene() is self:
                self.removeItem(self._stroke_item)
        except (AttributeError, RuntimeError):
            pass
        self._stroke_item = None

    def _document_size(self) -> Optional[tuple[int, int]]:
        if not self.views():
            return None
        view = self.views()[0]
        if not hasattr(view, "document_size"):
            return None
        width, height = view.document_size()
        return max(1, int(round(width))), max(1, int(round(height)))

    def _document_absolute_origin(self) -> QPointF:
        if not self.views():
            return QPointF(0.0, 0.0)
        view = self.views()[0]
        if not hasattr(view, "document_origin"):
            return QPointF(0.0, 0.0)
        return QPointF(view.document_origin())

    def _document_display_origin(self) -> QPointF:
        rect = BrushScene._document_rect(self)
        if rect is not None:
            return QPointF(rect.topLeft())
        return self._document_absolute_origin()

    def _scene_point_to_document_local(
        self,
        scene_point: Optional[QPointF],
    ) -> Optional[QPointF]:
        bounded_point = self._clamp_scene_point_to_document(scene_point)
        if bounded_point is None:
            return None
        origin = self._document_display_origin()
        return QPointF(
            bounded_point.x() - origin.x(),
            bounded_point.y() - origin.y(),
        )

    def _layer_absolute_origin(self, item) -> QPointF:
        positions = getattr(self, "original_item_positions", None)
        if isinstance(positions, dict):
            try:
                if item in positions:
                    return QPointF(positions[item])
            except TypeError:
                pass

        settings = getattr(item, "drawing_pad_settings", None)
        if settings is not None:
            return QPointF(
                float(getattr(settings, "x_pos", 0) or 0),
                float(getattr(settings, "y_pos", 0) or 0),
            )

        if not hasattr(item, "pos") or not self.views():
            return QPointF(0.0, 0.0)

        view = self.views()[0]
        canvas_offset = getattr(view, "canvas_offset", QPointF(0.0, 0.0))
        grid_compensation = getattr(
            view,
            "grid_compensation_offset",
            getattr(view, "_grid_compensation_offset", QPointF(0.0, 0.0)),
        )
        view_state = ViewState(
            canvas_offset=QPointF(canvas_offset),
            grid_compensation=QPointF(grid_compensation),
        )
        return CanvasPositionManager.display_to_absolute(
            item.pos(),
            view_state,
        )

    def _build_document_stroke_base(self, item) -> Optional[QImage]:
        qimage = getattr(item, "qimage", None)
        if qimage is None:
            return None

        document_size = self._document_size()
        if document_size is None:
            return qimage.copy()

        document_width, document_height = document_size
        base_image = QImage(
            document_width,
            document_height,
            QImage.Format.Format_ARGB32,
        )
        base_image.fill(Qt.GlobalColor.transparent)

        item_origin = self._layer_absolute_origin(item)
        document_origin = self._document_absolute_origin()
        target_x = int(round(item_origin.x() - document_origin.x()))
        target_y = int(round(item_origin.y() - document_origin.y()))

        painter = QPainter(base_image)
        painter.drawImage(target_x, target_y, qimage)
        painter.end()
        return base_image

    def _stroke_item_z_value(self) -> float:
        active_item = self._stroke_target_item or self.active_item
        if active_item is not None and hasattr(active_item, "zValue"):
            try:
                return float(active_item.zValue()) + 1.0
            except (TypeError, ValueError):
                pass
        return 3.0

    def _sync_stroke_item(self) -> None:
        if self._stroke_buffer_image is None:
            self._remove_stroke_item()
            return
        if self._stroke_item is None:
            self._stroke_item = QGraphicsPixmapItem()
            self._stroke_item.setAcceptedMouseButtons(
                Qt.MouseButton.NoButton
            )
            self.addItem(self._stroke_item)
        self._stroke_item.setPixmap(
            QPixmap.fromImage(self._stroke_buffer_image)
        )
        self._stroke_item.setPos(self._document_display_origin())
        self._stroke_item.setZValue(self._stroke_item_z_value())

    def _current_paint_target(self):
        if self.drawing_pad_settings.mask_layer_enabled:
            return self.mask_image
        layer_item = BrushScene._resolve_layer_canvas_item(self)
        if layer_item and getattr(layer_item, "qimage", None):
            return layer_item.qimage
        if BrushScene._scene_uses_layer_canvas(self):
            return None
        return self.image

    def _stroke_composition_mode(self, erasing: bool):
        if erasing and not self.drawing_pad_settings.mask_layer_enabled:
            return QPainter.CompositionMode.CompositionMode_DestinationOut
        return QPainter.CompositionMode.CompositionMode_SourceOver

    def _compose_stroke_image(
        self,
        base_image: Optional[QImage],
        stroke_image: Optional[QImage],
        erasing: bool,
    ) -> Optional[QImage]:
        if base_image is None:
            return None
        composed = base_image.copy()
        if stroke_image is None:
            return composed
        painter = QPainter(composed)
        painter.setCompositionMode(self._stroke_composition_mode(erasing))
        painter.drawImage(0, 0, stroke_image)
        painter.end()
        return composed

    def _start_stroke_buffer(self) -> None:
        base_image = self._current_paint_target()
        if base_image is None:
            self._clear_stroke_buffer()
            return
        self._stroke_base_image = base_image
        self._stroke_target_item = None
        self._stroke_target_layer_id = None
        if not self.drawing_pad_settings.mask_layer_enabled:
            self._stroke_target_item = BrushScene._resolve_layer_canvas_item(
                self
            )
            self._stroke_target_layer_id = getattr(
                self._stroke_target_item,
                "layer_id",
                None,
            )
            if self._stroke_target_layer_id is None:
                get_layer_id = getattr(
                    self,
                    "_get_current_selected_layer_id",
                    None,
                )
                if callable(get_layer_id):
                    try:
                        self._stroke_target_layer_id = get_layer_id()
                    except Exception:
                        self._stroke_target_layer_id = None
            if self._stroke_target_item is not None:
                document_base = self._build_document_stroke_base(
                    self._stroke_target_item
                )
                if document_base is not None:
                    self._stroke_base_image = document_base
        self._stroke_buffer_erasing = (
            not self.drawing_pad_settings.mask_layer_enabled
            and self.current_tool is CanvasToolName.ERASER
        )
        if self.drawing_pad_settings.mask_layer_enabled:
            width = base_image.width()
            height = base_image.height()
        else:
            document_size = self._document_size()
            if document_size is None:
                width = base_image.width()
                height = base_image.height()
            else:
                width, height = document_size
        self._stroke_buffer_image = QImage(
            width,
            height,
            QImage.Format.Format_ARGB32,
        )
        self._stroke_buffer_image.fill(Qt.GlobalColor.transparent)
        if (
            not self.drawing_pad_settings.mask_layer_enabled
            and not self._stroke_buffer_erasing
        ):
            self._sync_stroke_item()

    def _preview_document_stroke(self) -> bool:
        if (
            self.drawing_pad_settings.mask_layer_enabled
            or self._stroke_buffer_image is None
        ):
            return False

        if self._stroke_buffer_erasing:
            preview_item = self._stroke_target_item or self.active_item
            preview_image = self._compose_stroke_image(
                self._stroke_base_image,
                self._stroke_buffer_image,
                True,
            )
            self._update_item_image(
                preview_item,
                preview_image,
                invalidate_scene=False,
            )
            if preview_item is not None and hasattr(preview_item, "setPos"):
                preview_item.setPos(self._document_display_origin())
            return True

        self._sync_stroke_item()
        if self._stroke_item is not None and self._stroke_item.scene():
            self._stroke_item.scene().update(
                self._stroke_item.sceneBoundingRect()
            )
        return True

    def _update_active_item_image(
        self,
        image: Optional[QImage],
        *,
        invalidate_scene: bool = True,
    ) -> None:
        BrushScene._update_item_image(
            self,
            self.active_item,
            image,
            invalidate_scene=invalidate_scene,
        )

    def _update_item_image(
        self,
        item,
        image: Optional[QImage],
        *,
        invalidate_scene: bool = True,
    ) -> None:
        if image is None or item is None:
            return
        if hasattr(item, "updateImage"):
            item.updateImage(
                image,
                invalidate_scene=invalidate_scene,
            )
            if invalidate_scene and item.scene():
                item.scene().update(item.sceneBoundingRect())
            return
        if hasattr(item, "setPixmap"):
            item.setPixmap(QPixmap.fromImage(image))

    def _rebind_active_painter(self):
        if self._stroke_buffer_image is not None:
            self.set_painter(self._stroke_buffer_image)
            return

        target_image = self._current_paint_target()

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
            self._painter_target
            self._rebind_active_painter()
            painter = self.painter
            if painter is None:
                return
            needs_pen_setup = True
            if ensure_start or ensure_last:
                self._last_draw_scene_pos = self.last_pos or self.start_pos

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
        if (
            self._stroke_buffer_image is not None
            and erasing
            and not self.drawing_pad_settings.mask_layer_enabled
        ):
            pen_color = QColor(Qt.GlobalColor.white)
        pen_width = max(1, int(self.brush_settings.size))

        if new_stroke:
            self._last_draw_scene_pos = self.start_pos

        if needs_pen_setup or new_stroke or self.pen is None:
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

        current_pos = self._clamp_scene_point_to_document(self.last_pos)
        if current_pos is None:
            return

        previous_pos = self._clamp_scene_point_to_document(
            self._last_draw_scene_pos
        )
        if previous_pos is None:
            self._last_draw_scene_pos = current_pos
            return

        viewport_delta = current_pos - previous_pos
        if abs(viewport_delta.x()) < 0.01 and abs(viewport_delta.y()) < 0.01:
            return

        if (
            not self.drawing_pad_settings.mask_layer_enabled
            and self._stroke_buffer_image is not None
        ):
            image_start_pos = self._scene_point_to_document_local(
                previous_pos
            )
            image_last_pos = self._scene_point_to_document_local(current_pos)
        else:
            item_pos = (
                self.active_item.pos()
                if self.active_item
                else QPointF(0, 0)
            )
            image_start_pos = previous_pos - item_pos
            image_last_pos = current_pos - item_pos

        if image_start_pos is None or image_last_pos is None:
            self._last_draw_scene_pos = current_pos
            self.start_pos = current_pos
            return

        control_point = QPointF(
            (image_start_pos.x() + image_last_pos.x()) * 0.5,
            (image_start_pos.y() + image_last_pos.y()) * 0.5,
        )

        segment_path = QPainterPath(image_start_pos)
        segment_path.quadTo(control_point, image_last_pos)

        painter.drawPath(segment_path)

        self._last_draw_scene_pos = current_pos
        self.start_pos = current_pos

        if self._preview_document_stroke():
            return

        active_image = self.active_image
        if self._stroke_base_image is not None:
            active_image = self._compose_stroke_image(
                self._stroke_base_image,
                self._stroke_buffer_image,
                self._stroke_buffer_erasing,
            )

        self._update_active_item_image(
            active_image,
            invalidate_scene=False,
        )

    def _ensure_draw_space(self, scene_point: QPointF) -> bool:
        if scene_point is None:
            return False
        if self.drawing_pad_settings.mask_layer_enabled:
            return False
        item = BrushScene._resolve_layer_canvas_item(self)
        if (
            item is None
            and not BrushScene._scene_uses_layer_canvas(self)
            and self.item is not None
        ):
            item = self.item
        if item is None:
            return False
        # Only ensure/expand draw space when the user is actively drawing
        # with the brush or eraser. This prevents incidental expansion of
        # layer surfaces during non-drawing actions like panning,
        # recentring, or simple redraws which can otherwise trigger
        # quantized growth (surface growth step) and cause images to
        # become larger than their generated size.
        if not self.draw_button_down:
            return False
        if self.current_tool not in [
            CanvasToolName.BRUSH,
            CanvasToolName.ERASER,
        ]:
            return False
        if BrushScene._scene_uses_layer_canvas(self):
            # Layer-backed canvases use fixed layer surfaces while brushing.
            # Auto-growing smaller layers during a stroke shifts their stored
            # origin and makes partial-size images jump when drawing left/top.
            return False
        if self._active_item_uses_document_surface(item):
            return False

        radius = (self.brush_settings.size or 1) * 0.5 + 8
        return self._ensure_item_contains_scene_point(
            item, scene_point, radius
        )

    def _active_item_uses_document_surface(self, item) -> bool:
        if item is None or not self.views():
            return False
        document_rect = BrushScene._document_rect(self)
        if document_rect is None:
            return False
        if item.sceneBoundingRect().contains(document_rect):
            return True

        qimage = getattr(item, "qimage", None)
        view = self.views()[0]
        if qimage is None or not hasattr(view, "document_size"):
            return False

        document_width, document_height = view.document_size()
        return (
            qimage.width() == int(round(document_width))
            and qimage.height() == int(round(document_height))
        )

    def _document_rect(self) -> Optional[QRectF]:
        if not self.views():
            return None
        view = self.views()[0]
        if not hasattr(view, "document_rect"):
            return None
        rect = view.document_rect()
        if rect is None or rect.isEmpty():
            return None

        canvas_offset = getattr(view, "canvas_offset", QPointF(0.0, 0.0))
        grid_compensation = getattr(
            view,
            "grid_compensation_offset",
            getattr(view, "_grid_compensation_offset", QPointF(0.0, 0.0)),
        )
        view_state = ViewState(
            canvas_offset=QPointF(canvas_offset),
            grid_compensation=QPointF(grid_compensation),
        )
        display_origin = CanvasPositionManager.absolute_to_display(
            rect.topLeft(),
            view_state,
        )
        return QRectF(
            display_origin.x(),
            display_origin.y(),
            rect.width(),
            rect.height(),
        )

    def _scene_point_in_document(self, scene_point: Optional[QPointF]) -> bool:
        if scene_point is None:
            return False
        document_rect = self._document_rect()
        if document_rect is None:
            return True
        return document_rect.contains(scene_point)

    def _clamp_scene_point_to_document(
        self, scene_point: Optional[QPointF]
    ) -> Optional[QPointF]:
        if scene_point is None:
            return None
        document_rect = self._document_rect()
        if document_rect is None:
            return QPointF(scene_point)
        return QPointF(
            min(
                max(scene_point.x(), document_rect.left()),
                document_rect.right(),
            ),
            min(
                max(scene_point.y(), document_rect.top()),
                document_rect.bottom(),
            ),
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
        super()._handle_left_mouse_press(event)
        start_pos = event.scenePos()
        if not self._scene_point_in_document(start_pos):
            self.draw_button_down = False
            self.start_pos = None
            self.last_pos = None
            self._last_draw_scene_pos = None
            return

        bounded_start = self._clamp_scene_point_to_document(start_pos)
        # Use scenePos() so this matches the scene's offset
        self.draw_button_down = True
        self.start_pos = bounded_start
        self.last_pos = bounded_start
        self._last_draw_scene_pos = bounded_start
        if self._ensure_draw_space(self.start_pos):
            self._rebind_active_painter()
        if (
            self.drawing_pad_settings.mask_layer_enabled
            and self.mask_image is None
        ):
            self._create_mask_image()
        if self.is_brush_or_eraser:
            self._pending_brush_history_layer = self._add_image_to_undo()
            self._start_stroke_buffer()
        self._rebind_active_painter()
        return

    def mouseMoveEvent(self, event):
        # Update last_pos with scenePos() for consistent drawing
        self.last_pos = event.scenePos()
        if self._ensure_draw_space(self.last_pos):
            self._rebind_active_painter()
        super().mouseMoveEvent(event)

    def _handle_left_mouse_release(self, event) -> bool:
        self.draw_button_down = False

        merged_image = self.active_image
        if self._stroke_base_image is not None:
            merged_image = self._compose_stroke_image(
                self._stroke_base_image,
                self._stroke_buffer_image,
                self._stroke_buffer_erasing,
            )

        self.stop_painter()

        if self.drawing_pad_settings.mask_layer_enabled:
            self._update_active_item_image(merged_image)
            if merged_image is not None:
                self.mask_image = merged_image
            mask_source = merged_image if merged_image is not None else self.mask_image
            if mask_source is None:
                self._clear_stroke_buffer()
                return super()._handle_left_mouse_release(event)
            mask_image: Image = ImageQt.fromqimage(mask_source)
            mask_image = mask_image.convert("L").point(
                lambda p: 255 if p > 128 else 0
            )
            base_64_image = convert_image_to_binary(mask_image)
            self.update_drawing_pad_settings(mask=base_64_image)
        else:
            if merged_image is not None:
                target_item = self._stroke_target_item
                target_layer_id = self._stroke_target_layer_id
                document_display_origin = self._document_display_origin()
                document_absolute_origin = self._document_absolute_origin()

                if target_item is not None:
                    self._update_item_image(target_item, merged_image)
                    if hasattr(target_item, "setPos"):
                        target_item.setPos(document_display_origin)
                    if hasattr(self, "original_item_positions"):
                        self.original_item_positions[target_item] = QPointF(
                            document_absolute_origin
                        )
                    if hasattr(target_item, "layer_image_data"):
                        target_item.layer_image_data["pos_x"] = int(
                            round(document_absolute_origin.x())
                        )
                        target_item.layer_image_data["pos_y"] = int(
                            round(document_absolute_origin.y())
                        )

                pil_image = ImageQt.fromqimage(merged_image).copy()
                rgba_image = (
                    pil_image
                    if pil_image.mode == "RGBA"
                    else pil_image.convert("RGBA")
                )
                width, height = rgba_image.size
                raw_binary = (
                    b"AIRAW1"
                    + width.to_bytes(4, "big")
                    + height.to_bytes(4, "big")
                    + rgba_image.tobytes()
                )

                current_layer_id = None
                get_layer_id = getattr(
                    self,
                    "_get_current_selected_layer_id",
                    None,
                )
                if callable(get_layer_id):
                    try:
                        current_layer_id = get_layer_id()
                    except Exception:
                        current_layer_id = None

                if current_layer_id == target_layer_id:
                    self.current_active_image = pil_image
                    self._pending_image_binary = raw_binary
                    self._current_active_image_binary = raw_binary
                else:
                    self._pending_image_binary = None
                    self._current_active_image_binary = None

                try:
                    self.update_drawing_pad_settings(
                        layer_id=target_layer_id,
                        image=raw_binary,
                        x_pos=int(round(document_absolute_origin.x())),
                        y_pos=int(round(document_absolute_origin.y())),
                    )
                except Exception:
                    self.drawing_pad_settings.image = raw_binary

        self._clear_stroke_buffer()

        self.api.art.canvas.image_updated()
        if self.drawing_pad_settings.mask_layer_enabled:
            self.initialize_image()
            self.api.art.canvas.mask_updated()

        if self._pending_brush_history_layer is not None:
            self._commit_layer_history_transaction(
                self._pending_brush_history_layer, "image"
            )
            self._pending_brush_history_layer = None

        self._last_draw_scene_pos = None

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
