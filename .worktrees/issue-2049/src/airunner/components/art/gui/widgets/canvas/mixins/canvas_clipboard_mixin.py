"""Canvas clipboard operations mixin.

This mixin provides clipboard paste functionality for loading images from
the system clipboard into the canvas.
"""

import io
from typing import Optional

from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage


class CanvasClipboardMixin:
    """Mixin for canvas clipboard paste operations.

    Handles pasting images from system clipboard, including QImage data,
    raw image bytes, URLs, and text URLs.
    """

    def on_paste_image_from_clipboard(self) -> None:
        """Handle paste image from clipboard signal.

        Retrieves image from clipboard and loads it onto the canvas with
        undo history support.
        """
        img = self._paste_image_from_clipboard()
        if img is not None:
            layer_id = self._add_image_to_undo()
            if self.application_settings.resize_on_paste:
                img = self._resize_image(img)
            self.current_active_image = img
            self.initialize_image(img)
            self._commit_layer_history_transaction(layer_id, "image")

    def _paste_image_from_clipboard(self) -> Optional[Image.Image]:
        """Retrieve image from system clipboard.

        Attempts multiple strategies to extract image data from clipboard:
        1. QImage data (from Qt applications)
        2. Raw image bytes (PNG, JPEG, etc.)
        3. URLs to images
        4. Text URLs to images

        Returns:
            PIL Image in RGBA format, or None if no image found.
        """
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        self.logger.debug(f"Clipboard mime types: {mime.formats()}")

        # Try QImage data first
        img = self._try_qimage_from_clipboard(mime, clipboard)
        if img:
            return img

        # Try raw image data
        img = self._try_raw_image_from_clipboard(mime)
        if img:
            return img

        # Try URLs
        img = self._try_url_from_clipboard(mime)
        if img:
            return img

        # Try text URLs
        img = self._try_text_url_from_clipboard(mime)
        if img:
            return img

        self.logger.warning("No image found in clipboard for paste.")
        return None

    def _try_qimage_from_clipboard(
        self, mime, clipboard
    ) -> Optional[Image.Image]:
        """Try to extract QImage from clipboard.

        Args:
            mime: MIME data from clipboard.
            clipboard: Qt clipboard object.

        Returns:
            PIL Image if successful, None otherwise.
        """
        if mime.hasImage():
            qimg = clipboard.image()
            if not qimg.isNull():
                buffer = QImage(qimg)
                ptr = buffer.bits()
                ptr.setsize(buffer.sizeInBytes())
                img = Image.frombuffer(
                    "RGBA",
                    (buffer.width(), buffer.height()),
                    bytes(ptr),
                    "raw",
                    "BGRA",
                )
                return img
        return None

    def _try_raw_image_from_clipboard(self, mime) -> Optional[Image.Image]:
        """Try to extract raw image bytes from clipboard.

        Args:
            mime: MIME data from clipboard.

        Returns:
            PIL Image if successful, None otherwise.
        """
        for fmt in mime.formats():
            if not fmt.startswith("image/"):
                continue

            data = mime.data(fmt)
            # Try PyQt6/PySide6 QByteArray .data() and bytes()
            for get_bytes in (lambda d: d.data(), bytes):
                try:
                    data_bytes = get_bytes(data)
                    if not data_bytes or len(data_bytes) < 10:
                        continue
                    img = Image.open(io.BytesIO(data_bytes))
                    img.verify()
                    img = Image.open(io.BytesIO(data_bytes))
                    self.logger.debug(
                        f"Loaded image from clipboard mime {fmt} using "
                        f"{get_bytes.__name__}"
                    )
                    return img
                except Exception as e:
                    self.logger.error(
                        f"Failed to load image from clipboard mime {fmt} "
                        f"using {get_bytes.__name__}: {e}"
                    )
        return None

    def _try_url_from_clipboard(self, mime) -> Optional[Image.Image]:
        """Try to load image from URL in clipboard.

        Args:
            mime: MIME data from clipboard.

        Returns:
            PIL Image if successful, None otherwise.
        """
        if mime.hasUrls():
            for url in mime.urls():
                url_str = url.toString()
                img = self._load_image_from_url_or_file(url_str)
                if img is not None:
                    return img
        return None

    def _try_text_url_from_clipboard(self, mime) -> Optional[Image.Image]:
        """Try to load image from text URL in clipboard.

        Args:
            mime: MIME data from clipboard.

        Returns:
            PIL Image if successful, None otherwise.
        """
        if mime.hasText():
            text = mime.text()
            if (
                text.startswith("http://")
                or text.startswith("https://")
                or text.startswith("file://")
            ):
                img = self._load_image_from_url_or_file(text)
                if img is not None:
                    return img
        return None
