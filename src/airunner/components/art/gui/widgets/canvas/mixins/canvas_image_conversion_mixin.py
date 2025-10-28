"""Mixin for handling PIL Image to QImage conversion and caching."""

from typing import Optional

import PIL
from PIL import Image, ImageQt
from PySide6.QtGui import QImage

from airunner.utils.image import convert_binary_to_image


class CanvasImageConversionMixin:
    """Handles PIL Image <-> QImage conversion with intelligent caching.

    This mixin provides optimized methods for converting between PIL Images
    and QImages, with caching to avoid redundant conversions.
    """

    def _convert_pil_to_qimage(
        self, pil_image: Image.Image
    ) -> Optional[QImage]:
        """Convert PIL Image to QImage safely.

        Args:
            pil_image: The PIL Image to convert.

        Returns:
            QImage instance or None if conversion fails.
        """
        try:
            return ImageQt.ImageQt(pil_image)
        except (AttributeError, IsADirectoryError, Exception):
            return None

    def _load_image_from_settings(self) -> Optional[Image.Image]:
        """Load PIL Image from settings binary data.

        Returns:
            PIL Image or None if loading fails.
        """
        try:
            base64image = self.current_settings.image
            if base64image is None:
                return None
            pil_image = convert_binary_to_image(base64image)
            if pil_image is not None:
                return pil_image.convert("RGBA")
        except (AttributeError, PIL.UnidentifiedImageError, Exception):
            pass
        return None

    def _binary_to_pil_fast(self, binary_data: bytes) -> Optional[Image.Image]:
        """Fast inverse for raw storage format; fallback to existing converter.

        Raw format layout: b"AIRAW1" + 4 bytes width + 4 bytes height + RGBA bytes.

        Args:
            binary_data: The binary data to convert.

        Returns:
            PIL Image or None if conversion fails.
        """
        if binary_data is None:
            return None
        try:
            if binary_data.startswith(b"AIRAW1") and len(binary_data) > 14:
                w = int.from_bytes(binary_data[6:10], "big")
                h = int.from_bytes(binary_data[10:14], "big")
                rgba = binary_data[14:]
                if len(rgba) == w * h * 4:
                    return Image.frombuffer(
                        "RGBA", (w, h), rgba, "raw", "RGBA", 0, 1
                    )
        except Exception:
            pass
        return convert_binary_to_image(binary_data)
