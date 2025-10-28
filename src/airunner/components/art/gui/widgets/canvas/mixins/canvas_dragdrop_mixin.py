"""Canvas drag and drop operations mixin.

This mixin provides drag-and-drop functionality for loading images onto
the canvas from files, URLs, and clipboard sources.
"""

import io
import os
from typing import Optional

import requests
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent
from PySide6.QtWidgets import QApplication, QGraphicsScene
from PySide6.QtGui import QImage


class CanvasDragDropMixin:
    """Mixin for canvas drag-and-drop image operations.

    Handles dragging and dropping images from filesystem URLs, HTTP URLs,
    and clipboard data onto the canvas scene.
    """

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event for images.

        Args:
            event: Drag enter event containing potential image data.
        """
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                url_str = url.toString()
                if url_str.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".bmp", ".gif")
                ) or url_str.startswith("http"):
                    event.acceptProposedAction()
                    return
            event.ignore()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move event for images.

        Args:
            event: Drag move event containing potential image data.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event for images.

        Attempts to load dropped image from raw image data, URLs, or file
        paths. Updates canvas with the loaded image and creates undo
        history entry.

        Args:
            event: Drop event containing image data.
        """
        mime = event.mimeData()
        if hasattr(self, "logger"):
            self.logger.debug(f"Drop mime types: {mime.formats()}")

        handled = self._handle_raw_image_drop(mime)

        if not handled and mime.hasUrls():
            handled = self._handle_url_drop(mime)

        if handled:
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def _handle_raw_image_drop(self, mime) -> bool:
        """Handle drop of raw image data.

        Args:
            mime: MIME data from drop event.

        Returns:
            True if image was successfully loaded, False otherwise.
        """
        for fmt in mime.formats():
            if not fmt.startswith("image/"):
                continue

            data = mime.data(fmt)
            if data.size() < 10:
                continue

            data_bytes = data.data()
            if not data_bytes or len(data_bytes) < 10:
                continue

            try:
                img = Image.open(io.BytesIO(data_bytes))
                img.verify()
                img = Image.open(io.BytesIO(data_bytes))
                self._process_dropped_image(img)
                return True
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.debug(f"Failed to load image from {fmt}: {e}")
        return False

    def _handle_url_drop(self, mime) -> bool:
        """Handle drop of URL to image file.

        Args:
            mime: MIME data from drop event.

        Returns:
            True if image was successfully loaded, False otherwise.
        """
        for url in mime.urls():
            url_str = url.toString()
            img = self._load_image_from_url_or_file(url_str)
            if img is not None:
                self._process_dropped_image(img)
                return True

            path = url.toLocalFile()
            if path:
                img = self._load_image_from_url_or_file(path)
                if img is not None:
                    self._process_dropped_image(img)
                    return True
        return False

    def _process_dropped_image(self, img: Image.Image) -> None:
        """Process a dropped image and update canvas.

        Args:
            img: PIL Image to process and display.
        """
        layer_id = self._add_image_to_undo()

        if self.application_settings.resize_on_paste:
            img = self._resize_image(img)

        self.current_active_image = img

        try:
            self.initialize_image(img)
        except Exception:
            pass

        self._persist_dropped_image(img, layer_id)
        self._commit_layer_history_transaction(layer_id, "image")

        try:
            self.api.art.canvas.image_updated()
        except Exception:
            pass

    def _persist_dropped_image(self, img: Image.Image, layer_id: int) -> None:
        """Persist dropped image to database synchronously.

        Args:
            img: PIL Image to persist.
            layer_id: Layer ID for the image.
        """
        try:
            rgba_image = img if img.mode == "RGBA" else img.convert("RGBA")
            width, height = rgba_image.size
            raw_binary = (
                b"AIRAW1"
                + width.to_bytes(4, "big")
                + height.to_bytes(4, "big")
                + rgba_image.tobytes()
            )
            self.update_drawing_pad_settings(
                layer_id=layer_id, image=raw_binary
            )
            self._pending_image_binary = raw_binary
            self._current_active_image_binary = raw_binary
        except Exception:
            pass

    def _load_image_from_url_or_file(
        self, url_or_path: str
    ) -> Optional[Image.Image]:
        """Load an image from a local file or HTTP(S) URL.

        Args:
            url_or_path: URL or filesystem path to image.

        Returns:
            PIL Image in RGBA mode, or None if loading failed.
        """
        if url_or_path.startswith("http://") or url_or_path.startswith(
            "https://"
        ):
            try:
                resp = requests.get(url_or_path, timeout=10)
                resp.raise_for_status()
                return Image.open(io.BytesIO(resp.content)).convert("RGBA")
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.error(f"Failed to download image: {e}")
                return None
        elif url_or_path.startswith("file://"):
            path = url_or_path[7:]
            if os.path.exists(path):
                try:
                    return Image.open(path).convert("RGBA")
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.error(f"Failed to open file image: {e}")
            return None
        else:
            if os.path.exists(url_or_path):
                try:
                    return Image.open(url_or_path).convert("RGBA")
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.error(f"Failed to open file image: {e}")
            return None

    def _load_image_from_object(
        self,
        image: Image.Image,
        is_outpaint: bool = False,
        generated: bool = False,
    ) -> None:
        """Load an image from PIL Image object into scene.

        Args:
            image: PIL Image to load.
            is_outpaint: Whether this is an outpaint operation.
            generated: Whether this is a generated image.
        """
        self._add_image_to_scene(
            is_outpaint=is_outpaint, image=image, generated=generated
        )
