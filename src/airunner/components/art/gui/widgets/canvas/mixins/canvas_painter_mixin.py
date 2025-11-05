"""Mixin for managing QPainter instances on the canvas."""

from typing import Optional

from PySide6.QtGui import QImage, QPainter


class CanvasPainterMixin:
    """Handles QPainter creation, management, and lifecycle.

    This mixin provides methods for creating and managing QPainter instances
    for drawing operations on canvas images.
    """

    def stop_painter(self) -> None:
        """Stop the active QPainter if any and reset painter state."""
        if self.painter is not None:
            if self.painter.isActive():
                self.painter.end()
            self.painter = None
        self._painter_target = None

    def set_painter(self, image: Optional[QImage]) -> None:
        """Create and set a new QPainter for the given image.

        Args:
            image: The QImage to paint on. If None, no painter is created.
        """
        if image is None:
            return
        try:
            # Ensure any existing painter is fully stopped before rebinding
            self.stop_painter()
            self.painter = QPainter(image)
            self._painter_target = image
        except TypeError:
            self.painter = None
            self._painter_target = None

    def _release_painter_for_device(self, device: Optional[QImage]) -> None:
        """Release painter if it's currently bound to the specified device.

        Args:
            device: The QImage device to check against.
        """
        if device is not None and device is self._painter_target:
            self.stop_painter()
