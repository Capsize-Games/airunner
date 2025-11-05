"""Canvas image transformation operations mixin.

This mixin provides image transformation functionality including rotation,
resizing, copy, and cut operations for the canvas scene.
"""

import io
import subprocess
from typing import Optional

from PIL import Image
import PIL.Image


class CanvasTransformMixin:
    """Mixin for canvas image transformation operations.

    Handles rotation, resizing, copy, and cut operations on the active image
    layer with undo history support.
    """

    def on_canvas_copy_image_signal(self) -> None:
        """Handle canvas copy image signal.

        Copies the current active image to the system clipboard.
        """
        self._copy_image(self.current_active_image)

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

    def _move_pixmap_to_clipboard(
        self, image: Optional[Image.Image]
    ) -> Optional[Image.Image]:
        """Move image pixmap to system clipboard using xclip.

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

        data = io.BytesIO()
        image.save(data, format="png")
        data = data.getvalue()

        try:
            subprocess.Popen(
                ["xclip", "-selection", "clipboard", "-t", "image/png"],
                stdin=subprocess.PIPE,
            ).communicate(data)
        except FileNotFoundError:
            self.logger.error(
                "xclip not found. Cannot copy image to clipboard."
            )
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
