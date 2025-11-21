"""Mixin for handling canvas surface management and dynamic growth."""

import math
from typing import Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QPainter

from airunner.components.art.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)


class CanvasSurfaceManagementMixin:
    """Handles canvas surface creation, growth, and item positioning.

    This mixin manages dynamic canvas growth, surface creation, and item
    expansion to accommodate drawing operations beyond current boundaries.
    """

    def _create_blank_surface(
        self, width: Optional[int] = None, height: Optional[int] = None
    ) -> QImage:
        """Create a blank transparent QImage surface.

        Args:
            width: Width of the surface. If None, uses minimum surface size.
            height: Height of the surface. If None, uses minimum surface size.

        Returns:
            A new transparent QImage.
        """
        w = self._minimum_surface_size if width is None else max(1, width)
        h = self._minimum_surface_size if height is None else max(1, height)
        surface = QImage(w, h, QImage.Format.Format_ARGB32)
        surface.fill(Qt.GlobalColor.transparent)
        return surface

    def _quantize_growth(self, value: int) -> int:
        """Quantize growth values to surface growth step increments.

        Args:
            value: The growth value to quantize.

        Returns:
            Quantized growth value aligned to growth step.
        """
        if value <= 0:
            return 0
        step = self._surface_growth_step
        return max(step, int(math.ceil(value / step) * step))

    def _persist_item_origin(
        self, item: DraggablePixmap, origin: QPointF
    ) -> None:
        """Persist item origin position to database settings.

        Args:
            item: The draggable item whose position to persist.
            origin: The new origin position.
        """
        try:
            if isinstance(item, LayerImageItem) and item.layer_id is not None:
                self.update_drawing_pad_settings(
                    x_pos=int(origin.x()),
                    y_pos=int(origin.y()),
                    layer_id=item.layer_id,
                )
                if hasattr(item, "layer_image_data"):
                    item.layer_image_data["pos_x"] = int(origin.x())
                    item.layer_image_data["pos_y"] = int(origin.y())
            elif item is self.item:
                self.update_drawing_pad_settings(
                    x_pos=int(origin.x()),
                    y_pos=int(origin.y()),
                )
        except Exception as exc:
            self.logger.warning(
                f"Failed to persist item origin update: {exc}"
            )

    def _expand_item_surface(
        self,
        item: DraggablePixmap,
        grow_left: int,
        grow_top: int,
        grow_right: int,
        grow_bottom: int,
    ) -> bool:
        """Expand an item's surface in the specified directions.

        Args:
            item: The item whose surface to expand.
            grow_left: Pixels to add to the left.
            grow_top: Pixels to add to the top.
            grow_right: Pixels to add to the right.
            grow_bottom: Pixels to add to the bottom.

        Returns:
            True if expansion succeeded, False otherwise.
        """
        if not any([grow_left, grow_top, grow_right, grow_bottom]):
            return False

        qimage = self._get_item_qimage(item)
        if qimage is None:
            return False

        new_image = self._create_expanded_image(
            qimage, grow_left, grow_top, grow_right, grow_bottom
        )
        if new_image is None:
            return False

        if not self._apply_expanded_image(item, new_image):
            return False

        self._update_item_position_after_expansion(
            item, qimage, grow_left, grow_top, grow_right, grow_bottom
        )
        self._clear_image_caches()
        return True

    def _get_item_qimage(self, item: DraggablePixmap) -> Optional[QImage]:
        """Get QImage from item."""
        qimage = getattr(item, "qimage", None)
        if qimage is None and item is self.item:
            qimage = self.image
        return qimage

    def _create_expanded_image(
        self,
        qimage: QImage,
        grow_left: int,
        grow_top: int,
        grow_right: int,
        grow_bottom: int,
    ) -> Optional[QImage]:
        """Create expanded image with transparent padding."""
        new_width = qimage.width() + grow_left + grow_right
        new_height = qimage.height() + grow_top + grow_bottom
        if new_width <= 0 or new_height <= 0:
            return None

        new_image = QImage(new_width, new_height, QImage.Format.Format_ARGB32)
        new_image.fill(Qt.GlobalColor.transparent)

        self.stop_painter()
        painter = QPainter(new_image)
        painter.drawImage(grow_left, grow_top, qimage)
        painter.end()
        return new_image

    def _apply_expanded_image(
        self, item: DraggablePixmap, new_image: QImage
    ) -> bool:
        """Apply expanded image to item."""
        if hasattr(item, "updateImage"):
            try:
                item.updateImage(new_image)
            except Exception as e:
                self.logger.warning(f"Failed to update item image: {e}")
                return False
        else:
            return False

        if item is self.item:
            self.image = new_image
        return True

    def _update_item_position_after_expansion(
        self,
        item: DraggablePixmap,
        qimage: QImage,
        grow_left: int,
        grow_top: int,
        grow_right: int,
        grow_bottom: int,
    ) -> None:
        """Update item position and origin after expansion."""
        original_pos = self.original_item_positions.get(item)
        if original_pos is None:
            canvas_offset = self.get_canvas_offset()
            original_pos = item.pos() + canvas_offset

        new_origin = QPointF(
            original_pos.x() - grow_left, original_pos.y() - grow_top
        )
        self.original_item_positions[item] = new_origin

        self._log_expansion(
            item, qimage, grow_left, grow_top, grow_right, grow_bottom
        )
        self._persist_item_origin(item, new_origin)

        canvas_offset = self.get_canvas_offset()
        display_pos = QPointF(
            new_origin.x() - canvas_offset.x(),
            new_origin.y() - canvas_offset.y(),
        )
        item.setPos(display_pos)

    def _log_expansion(
        self,
        item: DraggablePixmap,
        qimage: QImage,
        grow_left: int,
        grow_top: int,
        grow_right: int,
        grow_bottom: int,
    ) -> None:
        """Log expansion details for debugging."""
        try:
            old_w, old_h = qimage.width(), qimage.height()
            new_w = old_w + grow_left + grow_right
            new_h = old_h + grow_top + grow_bottom
            self.logger.debug(
                f"Expanded item (layer_id={getattr(item, 'layer_id', None)}) "
                f"from {old_w}x{old_h} to {new_w}x{new_h} "
                f"(L{grow_left},T{grow_top},R{grow_right},B{grow_bottom})"
            )
        except Exception:
            pass

    def _clear_image_caches(self) -> None:
        """Clear image-related caches after expansion."""
        self._qimage_cache = None
        self._qimage_cache_size = None
        self._qimage_cache_hash = None
        self._current_active_image_ref = None

    def _ensure_item_contains_scene_point(
        self, item: DraggablePixmap, scene_point: QPointF, radius: float
    ) -> bool:
        """Ensure an item's surface contains a scene point with given radius.

        Expands the item's surface if necessary to contain the point.

        Args:
            item: The item to check/expand.
            scene_point: The scene point that must be contained.
            radius: The radius around the point to ensure is contained.

        Returns:
            True if item was expanded, False otherwise.
        """
        if item is None:
            return False
        if not hasattr(item, "mapFromScene"):
            return False

        qimage = getattr(item, "qimage", None)
        if qimage is None and item is self.item:
            qimage = self.image

        if qimage is None:
            return False

        local_point = item.mapFromScene(scene_point)
        radius = float(max(radius, 0.0))

        left_needed = self._quantize_growth(
            int(math.ceil(radius - local_point.x()))
        )
        top_needed = self._quantize_growth(
            int(math.ceil(radius - local_point.y()))
        )
        right_needed = self._quantize_growth(
            int(math.ceil(local_point.x() + radius - qimage.width()))
        )
        bottom_needed = self._quantize_growth(
            int(math.ceil(local_point.y() + radius - qimage.height()))
        )

        return self._expand_item_surface(
            item,
            max(0, left_needed),
            max(0, top_needed),
            max(0, right_needed),
            max(0, bottom_needed),
        )
