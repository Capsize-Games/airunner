"""Canvas active image property mixin for image caching and persistence."""

from typing import Optional
from PIL import Image
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import SettingsMixin
from airunner.utils.image import convert_binary_to_image


class CanvasActiveImageMixin(MediatorMixin, SettingsMixin):
    """Handles the current_active_image property with caching and persistence.

    This mixin provides functionality for:
    - Getting/setting the current active PIL Image
    - Fast caching to avoid redundant binary conversions
    - Debounced persistence to database
    - Support for raw RGBA storage format
    """

    @property
    def current_active_image(self) -> Optional[Image.Image]:
        """Get the current active PIL Image from settings with caching.

        Returns:
            The current active PIL Image, or None if no image is set.
        """
        if self._current_active_image_ref is not None:
            return self._current_active_image_ref

        binary_data = self.current_settings.image
        if binary_data is None:
            return None

        img = self._try_fast_decode(binary_data) or self._try_general_decode(
            binary_data
        )
        self._cache_decoded_image(img, binary_data)
        return img

    def _try_fast_decode(self, binary_data: bytes) -> Optional[Image.Image]:
        """Try fast AIRAW1 format decode."""
        if not (
            isinstance(binary_data, (bytes, bytearray))
            and binary_data.startswith(b"AIRAW1")
            and len(binary_data) >= 14
        ):
            return None

        try:
            w = int.from_bytes(binary_data[6:10], "big")
            h = int.from_bytes(binary_data[10:14], "big")
            rgba = binary_data[14:]
            if len(rgba) == w * h * 4:
                return Image.frombuffer(
                    "RGBA", (w, h), rgba, "raw", "RGBA", 0, 1
                ).copy()
        except Exception as e:
            self.logger.error(f"Error decoding AIRAW1 image: {e}")
        return None

    def _try_general_decode(self, binary_data: bytes) -> Optional[Image.Image]:
        """Try general format decode using converter."""
        try:
            return convert_binary_to_image(binary_data)
        except OSError as e:
            self.logger.error(f"Image format error (libpng/PIL): {e}")
        except Exception as e:
            self.logger.error(f"General error loading image: {e}")
        return None

    def _cache_decoded_image(
        self, img: Optional[Image.Image], binary_data: bytes
    ) -> None:
        """Cache decoded image and binary data."""
        self._current_active_image_ref = img
        self._current_active_image_binary = (
            binary_data if img is not None else None
        )

    @current_active_image.setter
    def current_active_image(self, image: Optional[Image.Image]) -> None:
        """Set the current active image and schedule a debounced persist.

        Heavy work (converting to bytes and writing to DB) is deferred to
        a QTimer tick to keep the UI responsive immediately after image load.

        Args:
            image: The PIL Image to set as active, or None to clear.
        """
        if image is not None and not isinstance(image, Image.Image):
            return

        if image is None:
            settings = self.current_settings  # cache to avoid double load
            if (
                settings.image is not None
                or self._pending_image_binary is not None
            ):
                # Clear pending and persisted
                self._pending_image_binary = None
                self._current_active_image_binary = None
                self._current_active_image_ref = None
                # Immediate flush
                self._update_current_settings("image", None)
                if self.settings_key == "drawing_pad_settings":
                    self.api.art.canvas.image_updated()
            return

        # Check lock before persisting any changes
        if getattr(self.current_settings, "lock_input_image", False):
            # User has locked the input image; do not persist changes
            # Still update in-memory reference for display but skip DB write
            self._current_active_image_ref = image
            return

        # Fast identity check: same object reference -> skip
        if image is self._current_active_image_ref:
            return

        # Update in-memory ref; binary will be produced during flush
        self._current_active_image_ref = image
        self._current_active_image_binary = None
        self._pending_image_ref = image
        self._pending_image_binary = None

        # Restart timer with configured debounce window
        self._persist_timer.start(self._persist_delay_ms)

    def _binary_to_pil_fast(self, binary_data: bytes) -> Optional[Image.Image]:
        """Fast inverse for raw storage format; fallback to existing converter.

        Raw format layout: b"AIRAW1" + 4 bytes width + 4 bytes height + RGBA bytes.

        Args:
            binary_data: Binary image data to decode.

        Returns:
            Decoded PIL Image or None if decoding fails.
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
