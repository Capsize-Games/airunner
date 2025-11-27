"""Canvas Generation Mixin.

Handles AI-generated image integration into the canvas including
placement, persistence, and history management.
"""

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

    def on_send_image_to_canvas_signal(self, data: Optional[Dict] = None):
        """Handle generated image by creating a new layer.

        Args:
            data: Dict containing 'image_response' with generated images
        """
        self.logger.info(f"[CANVAS DEBUG] on_send_image_to_canvas_signal called with data keys: {data.keys() if data else 'None'}")
        if data is None:
            self.logger.warning("[CANVAS DEBUG] data is None, returning early")
            return

        image_response = data.get("image_response")
        self.logger.info(f"[CANVAS DEBUG] image_response: {image_response}")
        self.cached_send_image_to_canvas = None
        if not image_response or not image_response.images:
            self.logger.warning(f"[CANVAS DEBUG] No images in response. image_response={image_response}, images={getattr(image_response, 'images', 'NO ATTR')}")
            return

        self.logger.info(f"[CANVAS DEBUG] Got {len(image_response.images)} images, first image: {image_response.images[0]}")
        image = image_response.images[0]

        # Get the current selected layer for the generated image
        layer_id = self._add_image_to_undo()
        self.logger.info(f"[CANVAS DEBUG] layer_id from _add_image_to_undo: {layer_id}")

        # Load the image to the scene (mark as generated for proper positioning)
        self.logger.info(f"[CANVAS DEBUG] Calling _load_image_from_object with image={image}, generated=True")
        self._load_image_from_object(image=image, generated=True)
        self.logger.info(f"[CANVAS DEBUG] _load_image_from_object completed")

        # Persist the image to the database
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
                layer_id=layer_id, image=raw_binary
            )
            self._pending_image_binary = raw_binary
            self._current_active_image_binary = raw_binary
        except Exception:
            pass

        # Commit to undo history
        self._commit_layer_history_transaction(layer_id, "image")

        # Defer layer display refresh to next event loop
        # This allows the canvas image to display immediately
        try:
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, self._refresh_layer_display)
        except Exception as e:
            self.logger.error(
                f"Failed to schedule layer display refresh: {e}",
                exc_info=True,
            )

        # Notify other components that the canvas image changed (matches drop/paste flow)
        try:
            if self.api and hasattr(self.api, "art"):
                self.api.art.canvas.image_updated()
        except Exception as e:
            self.logger.debug(f"image_updated notification failed: {e}")

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
