"""Canvas scene management mixin for image placement and display."""

from typing import Optional
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QImage
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.art.managers.stablediffusion.rect import Rect
import time


class CanvasSceneManagementMixin(MediatorMixin, SettingsMixin):
    """Handles image placement and scene management operations.

    This mixin provides functionality for:
    - Adding images to the canvas scene
    - Managing image positioning and caching
    - Handling outpaint operations
    - Optimizing QImage conversions with caching
    """

    def _add_image_to_scene(
        self,
        image: Image.Image,
        is_outpaint: bool = False,
        outpaint_box_rect: Optional[Rect] = None,
        generated: bool = False,
    ):
        """Add or update an image in the scene.

        Args:
            image: PIL Image to add to the scene.
            is_outpaint: Whether this is an outpaint operation.
            outpaint_box_rect: Optional bounding box for outpaint.
            generated: Whether this image was generated (vs user-imported).
        """
        self.logger.info(f"[SCENE DEBUG] _add_image_to_scene called: image={image}, generated={generated}")
        if image is None or not self._should_update_scene(generated):
            self.logger.warning(f"[SCENE DEBUG] Early return: image is None={image is None}, _should_update_scene={self._should_update_scene(generated)}")
            return

        canvas_offset = self.get_canvas_offset()
        root_point = self._calculate_root_point(
            outpaint_box_rect, is_outpaint, image, generated
        )
        self.logger.info(f"[SCENE DEBUG] canvas_offset={canvas_offset}, root_point={root_point}")
        self._update_or_create_item(image, root_point, canvas_offset)
        self.logger.info(f"[SCENE DEBUG] _update_or_create_item completed")

    def _should_update_scene(self, generated: bool) -> bool:
        """Check if scene should be updated based on lock state."""
        if generated and getattr(
            self.current_settings, "lock_input_image", False
        ):
            return False
        return True

    def _calculate_root_point(
        self,
        outpaint_box_rect: Optional[Rect],
        is_outpaint: bool,
        image: Image.Image,
        generated: bool,
    ) -> QPoint:
        """Calculate root point for image placement."""
        if outpaint_box_rect:
            if is_outpaint:
                _, root_point, _ = self._handle_outpaint(
                    outpaint_box_rect, image
                )
                return root_point
            return QPoint(outpaint_box_rect.x, outpaint_box_rect.y)

        if generated:
            return self._get_generated_image_position()

        return self._get_default_image_position()

    def _get_generated_image_position(self) -> QPoint:
        """Get position for generated images from active grid."""
        try:
            current_time = time.time()
            if (
                self._active_grid_cache is None
                or current_time - self._active_grid_cache_time > 1.0
            ):
                self._active_grid_cache = self.active_grid_settings
                self._active_grid_cache_time = current_time

            active_grid = self._active_grid_cache
            return QPoint(active_grid.pos_x, active_grid.pos_y)
        except Exception as e:
            self.logger.error(
                f"Failed to use active grid settings position: {e}"
            )
            return self._get_default_image_position()

    def _get_default_image_position(self) -> QPoint:
        """Get default position from drawing pad settings."""
        try:
            settings = self.drawing_pad_settings
            if settings.x_pos is not None and settings.y_pos is not None:
                return QPoint(settings.x_pos, settings.y_pos)
        except Exception as e:
            self.logger.warning(f"Error accessing drawing pad settings: {e}")
        return QPoint(0, 0)

    def _update_or_create_item(
        self, image: Image.Image, root_point: QPoint, canvas_offset: QPoint
    ) -> None:
        """Update existing item or create new one.

        Handles both the new layer-based system and legacy single-item system.
        Priority: active layer item > self.item > fallback to setting property.
        """
        # Try layer system first (new approach)
        active_layer_item = self._get_active_layer_item()
        self.logger.info(f"[ITEM DEBUG] active_layer_item={active_layer_item}, self.item={getattr(self, 'item', 'NO ATTR')}")
        if active_layer_item is not None:
            q_image = self._convert_and_cache_qimage(image)
            self.logger.info(f"[ITEM DEBUG] Using active layer item, q_image valid={q_image is not None and not q_image.isNull() if q_image else False}")
            if q_image is not None and not q_image.isNull():
                try:
                    active_layer_item.updateImage(q_image)
                    self.logger.info(
                        "Updated active layer item with filtered image"
                    )
                    # Also update current_active_image for consistency
                    self.current_active_image = image
                except Exception as e:
                    self.logger.error(f"Failed to update layer item: {e}")
            else:
                self.logger.warning(
                    "Skipped layer updateImage due to null QImage"
                )
            return

        # Fall back to legacy single-item system
        if self.item:
            self.logger.info(f"[ITEM DEBUG] Using legacy self.item system")
            q_image = self._convert_and_cache_qimage(image)
            if q_image is not None and not q_image.isNull():
                self._update_existing_item_image(q_image)
            else:
                self.logger.warning("Skipped updateImage due to null QImage")
            self._update_item_position(root_point, canvas_offset)
        else:
            # No item exists - CREATE a new one
            self.logger.info(f"[ITEM DEBUG] No item exists, creating new LayerImageItem")
            q_image = self._convert_and_cache_qimage(image)
            if q_image is not None and not q_image.isNull():
                self._create_new_item(q_image, root_point.x(), root_point.y())
                self.current_active_image = image
                self.logger.info(f"[ITEM DEBUG] Created new item at ({root_point.x()}, {root_point.y()})")
            else:
                self.logger.warning(f"[ITEM DEBUG] Cannot create item - QImage conversion failed")
                self.current_active_image = image

    def _convert_and_cache_qimage(
        self, image: Image.Image
    ) -> Optional[QImage]:
        """Convert PIL Image to QImage with caching.

        Args:
            image: PIL Image to convert.

        Returns:
            Converted QImage or None if conversion fails.
        """
        try:
            if self._is_cache_valid(image):
                return self._qimage_cache

            q_image = self._convert_pil_to_qimage_direct(image)
            self._cache_qimage(q_image, image)
            return q_image

        except Exception as e:
            self.logger.error(f"Failed to convert image to QImage: {e}")
            return self._fallback_conversion(image)

    def _is_cache_valid(self, image: Image.Image) -> bool:
        """Check if cached QImage is still valid."""
        # Use object identity instead of content hash for performance
        # Hash computation on 4MB images is too expensive (~700ms)
        image_id = id(image)
        return (
            self._qimage_cache is not None
            and self._qimage_cache_size == image.size
            and hasattr(self, "_qimage_cache_id")
            and self._qimage_cache_id == image_id
            and not self._qimage_cache.isNull()
        )

    def _convert_pil_to_qimage_direct(self, image: Image.Image) -> QImage:
        """Convert PIL Image to QImage using direct conversion."""
        import time

        start = time.time()

        if image.mode == "RGBA":
            w, h = image.size
            img_data = image.tobytes("raw", "RGBA")
            result = QImage(img_data, w, h, QImage.Format.Format_RGBA8888)
        elif image.mode == "RGB":
            w, h = image.size
            img_data = image.tobytes("raw", "RGB")
            result = QImage(img_data, w, h, QImage.Format.Format_RGB888)
        else:
            rgba_image = image.convert("RGBA")
            w, h = rgba_image.size
            img_data = rgba_image.tobytes("raw", "RGBA")
            result = QImage(img_data, w, h, QImage.Format.Format_RGBA8888)

        elapsed = (time.time() - start) * 1000
        if elapsed > 10:
            self.logger.warning(
                f"[PERF] PIL→QImage conversion took {elapsed:.1f}ms"
            )

        return result

    def _cache_qimage(self, q_image: QImage, image: Image.Image) -> None:
        """Cache the converted QImage."""
        # Use object identity instead of content hash for performance
        image_id = id(image)
        self._qimage_cache = q_image
        self._qimage_cache_size = image.size
        self._qimage_cache_id = image_id

    def _fallback_conversion(self, image: Image.Image) -> Optional[QImage]:
        """Fallback conversion using ImageQt."""
        try:
            rgba_image = image.convert("RGBA")
            return ImageQt(rgba_image)
        except Exception as e2:
            self.logger.error(f"Retry RGBA conversion failed: {e2}")
            return None

    def _update_existing_item_image(self, q_image: QImage) -> None:
        """Update the existing item's image.

        Args:
            q_image: QImage to set on the item.
        """
        try:
            # Stop any active painter before updating the image
            if self.painter and self.painter.isActive():
                self.painter.end()

            self.item.updateImage(q_image)
            # CRITICAL: Update self.image so drawing operations work
            # on the correct image
            self.image = q_image

            # Restart painter with new image
            self.set_painter(self.image)
        except Exception:
            pass
        # Check if item is still valid before using it
        try:
            if self.item is not None:
                self.item.setZValue(0)
        except (RuntimeError, AttributeError):
            # Item was deleted or is no longer valid
            pass

    def _update_item_position(
        self, root_point: QPoint, canvas_offset: QPointF
    ) -> None:
        """Update the item's position on the canvas.

        Args:
            root_point: Absolute position of the item.
            canvas_offset: Current canvas viewport offset.
        """
        try:
            absolute_pos = QPointF(root_point.x(), root_point.y())
            self.original_item_positions[self.item] = absolute_pos

            visible_pos_x = absolute_pos.x() - canvas_offset.x()
            visible_pos_y = absolute_pos.y() - canvas_offset.y()
            current_pos = self.item.pos()
            if (
                abs(current_pos.x() - visible_pos_x) > 0.5
                or abs(current_pos.y() - visible_pos_y) > 0.5
            ):
                self.item.setPos(visible_pos_x, visible_pos_y)
        except (RuntimeError, AttributeError):
            # Item was deleted or is no longer valid
            pass
