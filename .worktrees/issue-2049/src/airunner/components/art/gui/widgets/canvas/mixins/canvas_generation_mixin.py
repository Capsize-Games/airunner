"""Canvas Generation Mixin.

Handles AI-generated image integration into the canvas including
placement, persistence, and history management.
"""

from functools import partial
from typing import Optional, Dict


class CanvasGenerationMixin:
    """Provides AI image generation integration to canvas scenes.

    Handles:
    - Receiving generated images from AI models
    - Creating layers for generated images
    - Persisting generated images to database
    - Managing cached generation results
    """

    def handle_cached_send_image_to_canvas(self):
        """Process a cached generated image.

        Used when a generated image was cached and needs to be sent
        to the canvas after initialization.
        """
        image_response = self.cached_send_image_to_canvas
        if image_response:
            self.on_send_image_to_canvas_signal(
                {"image_response": image_response}
            )

    def _cache_pending_layer_image(self, layer_id, image) -> None:
        """Preserve a generated image for the next layer refresh."""
        if layer_id is None or image is None:
            return

        pending_layer_images = getattr(self, "_pending_layer_images", None)
        if not isinstance(pending_layer_images, dict):
            pending_layer_images = {}
            self._pending_layer_images = pending_layer_images

        pending_layer_images[layer_id] = image

    def on_send_image_to_canvas_signal(self, data: Optional[Dict] = None):
        """Handle generated image by creating a new layer.

        Args:
            data: Dict containing 'image_response' with generated images
        """
        self.logger.info(
            "[CANVAS DEBUG] on_send_image_to_canvas_signal keys=%s",
            list(data.keys()) if data else None,
        )
        if data is None:
            self.logger.debug(
                "[CANVAS DEBUG] data is None, returning early"
            )
            return

        image_response = data.get("image_response")
        self.cached_send_image_to_canvas = None
        if not image_response or not image_response.images:
            self.logger.debug(
                "[CANVAS DEBUG] No images in response. "
                "image_response=%s images=%s",
                image_response,
                getattr(image_response, "images", "NO ATTR"),
            )
            return

        image = image_response.images[0]

        # Get the current selected layer for the generated image
        layer_id = self._add_image_to_undo()
        self._cache_pending_layer_image(layer_id, image)
        self.logger.debug(
            "[CANVAS DEBUG] layer_id from _add_image_to_undo: %s",
            layer_id,
        )

        # Load the image to the scene (mark as generated for proper positioning)
        self.logger.info(
            "[CANVAS DEBUG] Calling _load_image_from_object; generated=True"
        )
        self._load_image_from_object(image=image, generated=True)
        self.logger.info(
            "[CANVAS DEBUG] _load_image_from_object completed"
        )
        self._force_canvas_viewport_refresh()
        self._notify_generated_image_ready()
        self._schedule_generated_follow_up(
            partial(self._finalize_generated_image, layer_id, image)
        )

        post_display_callback = getattr(
            image_response,
            "post_display_callback",
            None,
        )
        if callable(post_display_callback):
            self._schedule_generated_follow_up(post_display_callback)

    def _force_canvas_viewport_refresh(self) -> None:
        """Force all attached views to repaint the current scene content.

        After an image is added or updated via _update_or_create_item,
        the Qt paint system sometimes coalesces update regions in a way
        that skips the newly populated area.  An explicit deferred
        viewport repaint guarantees the generated image becomes visible.
        """
        from PySide6.QtCore import QTimer

        def _repaint_all_viewports():
            try:
                # Accessing QGraphicsItem.scene() may raise RuntimeError
                # if the underlying C++ object was deleted.
                for view in self.views():
                    viewport = view.viewport()
                    if viewport is not None:
                        viewport.repaint()
            except RuntimeError:
                pass

        # Defer one cycle to let any pending paint events be processed first
        QTimer.singleShot(0, _repaint_all_viewports)

    def _notify_generated_image_ready(self) -> None:
        """Notify the view layer so the new image can paint immediately."""
        try:
            if self.api and hasattr(self.api, "art"):
                self.api.art.canvas.image_updated()
        except Exception as exc:
            self.logger.debug(
                f"image_updated notification failed: {exc}"
            )

    def _schedule_generated_follow_up(self, callback) -> None:
        """Run heavy follow-up work after the first canvas update is queued."""
        try:
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, callback)
        except Exception as exc:
            self.logger.debug(
                f"Falling back to inline generated follow-up: {exc}"
            )
            callback()

    def _finalize_generated_image(self, layer_id, image) -> None:
        """Persist generated image state after the initial canvas handoff."""
        self._persist_generated_layer_image(layer_id, image)
        self._commit_layer_history_transaction(layer_id, "image")
        try:
            self._refresh_layer_display()
        except Exception as exc:
            self.logger.error(
                f"Failed to refresh layer display: {exc}",
                exc_info=True,
            )

    def _persist_generated_layer_image(self, layer_id, image) -> None:
        """Persist one generated image to layer storage."""
        try:
            rgba_image = (
                image if image.mode == "RGBA" else image.convert("RGBA")
            )
            width, height = rgba_image.size
            raw_binary = (
                b"AIRAW1"
                + width.to_bytes(4, "big")
                + height.to_bytes(4, "big")
                + rgba_image.tobytes()
            )
            self.update_drawing_pad_settings(
                layer_id=layer_id,
                image=raw_binary,
            )
            self._pending_image_binary = raw_binary
            self._current_active_image_binary = raw_binary
        except Exception:
            pass

    def on_image_generated_signal(self, data: Dict):
        """Handle image generation completion signal.

        Delegates to the appropriate handler based on generation code.

        Args:
            data: Dict containing:
                - code: Generation code identifying the operation
                - callback: Optional callback function to invoke
        """
        code = data["code"]
        callback = data.get("callback", None)
        self._handle_image_generated_signal(code, callback)

    def _handle_image_generated_signal(self, code: str, callback=None):
        """Process generated image based on operation code.

        Args:
            code: Operation code (e.g., "outpaint", "img2img")
            callback: Optional callback to invoke after processing
        """
        if code == "outpaint":
            self._handle_outpaint(callback)
        else:
            if callback:
                callback()

    def _handle_outpaint(self, callback=None):
        """Handle outpaint operation completion.

        Processes the expanded canvas after outpainting operation,
        updating the current image and clearing undo history.

        Args:
            callback: Optional callback to invoke after processing
        """
        image = self.current_active_image
        layer_id = None
        try:
            layer_id = self._get_current_selected_layer_id()
        except Exception:
            pass
        if layer_id is not None:
            self.update_drawing_pad_settings(layer_id=layer_id, image=image)
        else:
            self.current_active_image = image
        self._clear_history()
        if callback:
            callback()
