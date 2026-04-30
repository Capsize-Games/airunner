"""Canvas image transformation operations mixin.

This mixin provides image transformation functionality including rotation,
resizing, copy, and cut operations for the canvas scene.
"""

from math import ceil, floor
from typing import Optional

from PIL import Image, ImageQt
import PIL.Image
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QClipboard, QPainter


class CanvasTransformMixin:
    """Mixin for canvas image transformation operations.

    Handles rotation, resizing, copy, and cut operations on the active image
    layer with undo history support.
    """

    def on_canvas_copy_image_signal(self) -> None:
        """Handle canvas copy image signal.

        Copies the current active image to the system clipboard.
        """
        image = self._get_clipboard_source_image()
        if image is None:
            return
        self._copy_image(image)

    def _get_clipboard_source_image(self) -> Optional[Image.Image]:
        """Return the image that should be copied for the desktop canvas."""
        if not self._is_primary_canvas_scene():
            return None

        live_scene_image = self._get_live_scene_image()
        if live_scene_image is not None:
            return live_scene_image

        composed_image = self._get_composed_canvas_image()
        if composed_image is not None:
            return composed_image

        return self.current_active_image

    def _is_primary_canvas_scene(self) -> bool:
        """Return True when this scene represents the main desktop canvas."""
        return (
            getattr(self, "settings_key", None) == "drawing_pad_settings"
            and getattr(self, "canvas_type", None) in {"brush", "image"}
        )

    def _get_composed_canvas_image(self) -> Optional[Image.Image]:
        """Return the visible drawing-pad composition when available."""
        layer_compositor = getattr(self, "layer_compositor", None)
        compose_visible_layers = getattr(
            layer_compositor,
            "compose_visible_layers",
            None,
        )
        if not callable(compose_visible_layers):
            return None

        try:
            image = compose_visible_layers()
        except Exception as exc:
            self.logger.debug(
                "Failed to compose visible layers for clipboard copy: %s",
                exc,
            )
            return None

        if isinstance(image, Image.Image):
            return image
        return None

    def _get_live_scene_image(self) -> Optional[Image.Image]:
        """Return a composition of the currently visible in-memory scene."""
        composed_qimage = self._compose_live_scene_qimage()
        if composed_qimage is None or composed_qimage.isNull():
            pending_image = getattr(self, "_pending_image_ref", None)
            if isinstance(pending_image, Image.Image):
                return pending_image
            return None

        try:
            return ImageQt.fromqimage(composed_qimage)
        except Exception as exc:
            self.logger.debug(
                "Failed to convert live scene image for clipboard copy: %s",
                exc,
            )
            return None

    def _compose_live_scene_qimage(self) -> Optional[QImage]:
        """Compose the visible in-memory scene image items into one QImage."""
        visible_sources = self._get_visible_scene_image_sources()
        if not visible_sources:
            return None

        min_x = floor(min(source[0] for source in visible_sources))
        min_y = floor(min(source[1] for source in visible_sources))
        max_x = ceil(max(source[0] + source[2].width() for source in visible_sources))
        max_y = ceil(max(source[1] + source[2].height() for source in visible_sources))

        width = max_x - min_x
        height = max_y - min_y
        if width <= 0 or height <= 0:
            return None

        canvas = QImage(width, height, QImage.Format.Format_ARGB32)
        canvas.fill(0)

        painter = QPainter(canvas)
        try:
            for x_pos, y_pos, qimage, opacity, _z_value in visible_sources:
                painter.setOpacity(opacity)
                painter.drawImage(x_pos - min_x, y_pos - min_y, qimage)
        finally:
            painter.end()

        return canvas

    def _get_visible_scene_image_sources(self):
        """Collect visible scene image sources in z-order for composition."""
        sources = []
        layer_items = getattr(self, "_layer_items", {}) or {}
        pending_layer_images = getattr(self, "_pending_layer_images", {}) or {}

        for layer_id, item in layer_items.items():
            qimage = self._get_item_qimage(item)
            pending_image = pending_layer_images.get(layer_id)
            if isinstance(pending_image, Image.Image):
                qimage = self._convert_scene_source_to_qimage(pending_image)
            if qimage is None or qimage.isNull():
                continue
            if hasattr(item, "isVisible") and not item.isVisible():
                continue
            position = item.scenePos() if hasattr(item, "scenePos") else item.pos()
            opacity = item.opacity() if hasattr(item, "opacity") else 1.0
            z_value = item.zValue() if hasattr(item, "zValue") else 0
            sources.append((position.x(), position.y(), qimage, opacity, z_value))

        if not sources:
            legacy_item = getattr(self, "item", None)
            qimage = self._get_item_qimage(legacy_item)
            if qimage is not None and not qimage.isNull():
                if not hasattr(legacy_item, "isVisible") or legacy_item.isVisible():
                    position = (
                        legacy_item.scenePos()
                        if hasattr(legacy_item, "scenePos")
                        else legacy_item.pos()
                    )
                    opacity = (
                        legacy_item.opacity()
                        if hasattr(legacy_item, "opacity")
                        else 1.0
                    )
                    z_value = (
                        legacy_item.zValue()
                        if hasattr(legacy_item, "zValue")
                        else 0
                    )
                    sources.append(
                        (position.x(), position.y(), qimage, opacity, z_value)
                    )

        return sorted(sources, key=lambda source: source[4])

    @staticmethod
    def _get_item_qimage(item) -> Optional[QImage]:
        """Return the underlying QImage from a scene item when available."""
        if item is None:
            return None
        qimage = getattr(item, "qimage", None)
        if callable(qimage):
            qimage = qimage()
        return qimage

    def _convert_scene_source_to_qimage(
        self, image: Image.Image
    ) -> Optional[QImage]:
        """Convert a PIL image source into a QImage for live composition."""
        converter = getattr(self, "_convert_and_cache_qimage", None)
        if callable(converter):
            qimage = converter(image)
            if qimage is not None and not qimage.isNull():
                return qimage
        return self._pil_to_qimage(image)

    def on_canvas_cut_image_signal(self) -> None:
        """Handle canvas cut image signal.

        Copies the current active image to clipboard and deletes it from
        canvas.
        """
        self._cut_image(self.current_active_image)

    def on_canvas_rotate_90_clockwise_signal(self) -> None:
        """Handle rotate 90 degrees clockwise signal."""
        self._rotate_90_clockwise()

    def on_canvas_rotate_90_counterclockwise_signal(self) -> None:
        """Handle rotate 90 degrees counterclockwise signal."""
        self._rotate_90_counterclockwise()

    def rotate_image(self, angle: float) -> None:
        """Rotate the current active image by specified angle.

        Args:
            angle: Rotation angle in degrees. Positive is counterclockwise,
                negative is clockwise.
        """
        image = self.current_active_image
        if image is not None:
            layer_id = self._add_image_to_undo()
            image = image.rotate(angle, expand=True)
            self.current_active_image = image
            self.initialize_image(image)
            self._commit_layer_history_transaction(layer_id, "image")

    def _rotate_90_clockwise(self) -> None:
        """Rotate current image 90 degrees clockwise."""
        self.rotate_image(-90)

    def _rotate_90_counterclockwise(self) -> None:
        """Rotate current image 90 degrees counterclockwise."""
        self.rotate_image(90)

    def _copy_image(
        self, image: Optional[Image.Image]
    ) -> Optional[Image.Image]:
        """Copy image to system clipboard.

        Args:
            image: PIL Image to copy to clipboard.

        Returns:
            The same image if successful, None otherwise.
        """
        return self._move_pixmap_to_clipboard(image)

    def _pil_to_qimage(self, pil_image: Image.Image) -> QImage:
        """Convert PIL Image to QImage.
        
        Args:
            pil_image: PIL Image to convert.
            
        Returns:
            QImage equivalent of the PIL Image.
        """
        # Ensure image is in RGBA format
        if pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")
        
        # Get image data
        data = pil_image.tobytes("raw", "RGBA")
        width, height = pil_image.size
        
        # Create QImage from raw data
        qimage = QImage(data, width, height, QImage.Format.Format_RGBA8888)
        # Make a copy since the data buffer needs to persist
        return qimage.copy()

    def _move_pixmap_to_clipboard(
        self, image: Optional[Image.Image]
    ) -> Optional[Image.Image]:
        """Move image pixmap to system clipboard using Qt's clipboard.

        Uses Qt's QClipboard which works properly with X11 forwarding in Docker
        containers and doesn't require external tools like xclip.

        Args:
            image: PIL Image to copy to clipboard.

        Returns:
            The same image if successful, None otherwise.
        """
        if image is None:
            self.logger.warning("No image to copy to clipboard.")
            return None
        if not isinstance(image, Image.Image):
            self.logger.warning("Invalid image type.")
            return None

        try:
            # Convert PIL Image to QImage
            qimage = self._pil_to_qimage(image)
            
            # Get the system clipboard
            clipboard = QApplication.clipboard()
            
            if clipboard is None:
                self.logger.error("Could not access system clipboard")
                return None
            
            # Set the image on the clipboard
            clipboard.setImage(qimage, QClipboard.Mode.Clipboard)
            
            # Verify the copy worked by checking if clipboard has image
            if clipboard.mimeData() and clipboard.mimeData().hasImage():
                self.logger.info(f"Image copied to clipboard ({image.width}x{image.height})")
            else:
                self.logger.warning("Clipboard copy may have failed - no image detected after copy")
            
        except Exception as e:
            self.logger.error(f"Failed to copy image to clipboard: {e}")
            # Try fallback with xclip if Qt clipboard fails
            try:
                import subprocess
                import io
                data = io.BytesIO()
                image.save(data, format="png")
                data = data.getvalue()
                subprocess.Popen(
                    ["xclip", "-selection", "clipboard", "-t", "image/png"],
                    stdin=subprocess.PIPE,
                ).communicate(data)
                self.logger.info(f"Image copied to clipboard using xclip fallback ({image.width}x{image.height})")
            except FileNotFoundError:
                self.logger.error("xclip fallback also failed - xclip not found")
                return None
            except Exception as e2:
                self.logger.error(f"xclip fallback also failed: {e2}")
                return None
            
        return image

    def _cut_image(
        self, image: Optional[Image.Image] = None
    ) -> Optional[Image.Image]:
        """Cut image from canvas (copy and delete).

        Args:
            image: PIL Image to cut. Defaults to current active image.

        Returns:
            The copied image if successful, None otherwise.
        """
        image = self._copy_image(image)
        if image is not None:
            layer_id = self._add_image_to_undo()
            self.delete_image()
            self._commit_layer_history_transaction(layer_id, "image")
        return image

    def _resize_image(
        self, image: Optional[Image.Image]
    ) -> Optional[Image.Image]:
        """Resize image to fit within working dimensions.

        Thumbnails the image to fit within application_settings.working_width
        and working_height while maintaining aspect ratio.

        Args:
            image: PIL Image to resize.

        Returns:
            Resized PIL Image, or None if input image is None.
        """
        if image is None:
            return None

        max_size = (
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        image.thumbnail(max_size, PIL.Image.Resampling.BICUBIC)
        return image
