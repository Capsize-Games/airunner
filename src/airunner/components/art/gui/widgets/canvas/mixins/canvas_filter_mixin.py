"""Canvas filter operations mixin.

This mixin provides image filter application, preview, and cancellation
functionality for the canvas scene.
"""

from typing import Any, Optional

from PIL import Image


class CanvasFilterMixin:
    """Mixin for canvas image filter operations.

    Handles applying filters to the active image layer, previewing filters
    before committing, and cancelling filter previews.
    """

    def on_apply_filter_signal(self, message: Any) -> None:
        """Handle filter application signal.

        Args:
            message: Filter object or dict with 'filter_object' key containing
                the filter instance to apply.
        """
        if isinstance(message, dict) and "filter_object" in message:
            filter_object = message["filter_object"]
        else:
            filter_object = message
        self._apply_filter(filter_object)

    def on_cancel_filter_signal(self) -> None:
        """Handle filter cancellation signal.

        Restores the image to its pre-filter state if a preview was active.
        """
        image = self._cancel_filter()
        if image:
            self._load_image_from_object(image=image)

    def on_preview_filter_signal(self, message: dict) -> None:
        """Handle filter preview signal.

        Args:
            message: Dict with 'filter_object' key containing the filter to
                preview.
        """
        filter_object = message["filter_object"]
        filtered_image = self._preview_filter(
            self.current_active_image, filter_object
        )
        self._load_image_from_object(image=filtered_image)

    def _apply_filter(self, filter_object: Any) -> None:
        """Apply a filter to the current active image.

        Only works when drawing_pad_settings is active. Preserves undo state
        and commits changes to history.

        Args:
            filter_object: Filter instance with a filter() method that accepts
                a PIL Image and returns a filtered PIL Image.
        """
        if hasattr(self, "logger") and self.logger:
            self.logger.info(
                f"_apply_filter called with filter: {filter_object}"
            )
            self.logger.info(f"Settings key: {self.settings_key}")

        if self.settings_key != "drawing_pad_settings":
            if hasattr(self, "logger") and self.logger:
                self.logger.warning(
                    f"Filter not applied - wrong settings_key: {self.settings_key}"
                )
            return
        try:
            layer_id = self._add_image_to_undo()
            current = self.current_active_image
            if hasattr(self, "logger") and self.logger:
                self.logger.info(
                    f"Current active image: {current.size if current else None}"
                )
            if current is None:
                if hasattr(self, "logger") and self.logger:
                    self.logger.warning("No current active image to filter")
                return

            try:
                if hasattr(self, "logger") and self.logger:
                    self.logger.info(f"Applying filter to image...")
                filtered_image = filter_object.filter(current)
                if hasattr(self, "logger") and self.logger:
                    self.logger.info(
                        f"Filter applied successfully, result: {filtered_image.size if filtered_image else None}"
                    )
            except Exception:
                if hasattr(self, "logger") and self.logger:
                    self.logger.exception("Filter application failed")
                return

            self.previewing_filter = False
            self.image_backup = None
            self._load_image_from_object(image=filtered_image)
            self._flush_pending_image()
            self._commit_layer_history_transaction(layer_id, "image")
            if hasattr(self, "logger") and self.logger:
                self.logger.info("Filter applied and committed to history")
        except Exception:
            if hasattr(self, "logger") and self.logger:
                self.logger.exception("Unexpected error applying filter")

    def _cancel_filter(self) -> Optional[Image.Image]:
        """Cancel filter preview and restore backup image.

        Returns:
            Backup image if one exists, None otherwise.
        """
        image = None
        if self.image_backup:
            image = self.image_backup.copy()
            self.image_backup = None
        self.previewing_filter = False
        return image

    def _preview_filter(
        self, image: Optional[Image.Image], filter_object: Any
    ) -> Optional[Image.Image]:
        """Preview a filter on the current image without applying it.

        Creates a backup of the original image on first preview, allowing
        the user to cancel and restore. Subsequent previews reuse the backup.

        Args:
            image: PIL Image to preview filter on.
            filter_object: Filter instance with a filter() method.

        Returns:
            Filtered PIL Image, or None if preview is not applicable.
        """
        if self.settings_key != "drawing_pad_settings":
            return None
        if not image:
            return None

        if not self.previewing_filter:
            self.image_backup = image.copy()
            self.previewing_filter = True
        else:
            image = self.image_backup.copy()

        filtered_image = filter_object.filter(image)
        return filtered_image
