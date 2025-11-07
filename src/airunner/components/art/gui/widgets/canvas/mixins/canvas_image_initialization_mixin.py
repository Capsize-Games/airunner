"""Mixin for image initialization and scene management."""

from typing import Optional

from PIL import Image


class CanvasImageInitializationMixin:
    """Handles image initialization and scene setup.

    This mixin provides methods for initializing images on the canvas,
    managing image state, and handling scene updates.
    """

    def set_image(self, pil_image: Optional[Image.Image] = None) -> None:
        """Set the image for the scene from PIL Image or cached settings.

        Args:
            pil_image: Optional PIL Image to set. If None, loads from settings.
        """
        if not pil_image:
            # Use cached reference first to avoid database lookup
            pil_image = self._current_active_image_ref
            if pil_image is None:
                # Fallback to loading from database
                pil_image = self._load_image_from_settings()

        if pil_image is not None:
            self.image = self._convert_pil_to_qimage(pil_image)
        else:
            self.image = self._create_blank_surface()
            self._current_active_image_ref = None
            self._current_active_image_binary = None

    def initialize_image(
        self, image: Optional[Image.Image] = None, generated: bool = False
    ) -> None:
        """Initialize or update the canvas image and layers.

        Args:
            image: Optional PIL Image to initialize with. If None, uses current active image.
            generated: Whether this image was generated (affects positioning).
        """
        self.stop_painter()
        self.current_active_image = image
        self.set_image(image)

        x = self.active_grid_settings.pos_x
        y = self.active_grid_settings.pos_y

        self.update_drawing_pad_settings(
            x_pos=x,
            y_pos=y,
        )

        self.set_item(self.image, x=x, y=y)
        self.set_painter(self.image)

        # Initialize layers only for the main drawing pad scene
        if getattr(self, "canvas_type", None) == "drawing_pad":
            if not self._layers_initialized:
                self._layers_initialized = True
                self._refresh_layer_display()

        self.update()

        for view in self.views():
            view.viewport().update()
            view.update()
        self.update_image_position(self.get_canvas_offset())

    def refresh_image(self, image: Optional[Image.Image] = None) -> None:
        """Refresh the displayed image without losing viewport position.

        Args:
            image: Optional PIL Image to set. If None, uses current active image.
        """
        views = self.views()
        if not views:
            # No view attached, just reinitialize the image
            self.initialize_image(image)
            return

        view = views[0]
        current_viewport_rect = view.mapToScene(
            view.viewport().rect()
        ).boundingRect()

        if self.painter and self.painter.isActive():
            self.painter.end()
        # Accessing Qt objects can raise RuntimeError if the underlying
        # C++ object was deleted elsewhere. Catch both AttributeError
        # and RuntimeError to be defensive and avoid crashes.
        item_scene = None
        try:
            if hasattr(self, "item") and self.item is not None:
                item_scene = self.item.scene()
        except (AttributeError, RuntimeError):
            item_scene = None

        if item_scene is not None:
            try:
                item_scene.removeItem(self.item)
            except (RuntimeError, AttributeError):
                # Item was deleted or invalid; ignore and continue
                pass
        self.initialize_image(image)
        view.setSceneRect(current_viewport_rect)

    def delete_image(self) -> None:
        """Delete the current image from the scene and reset state."""
        # Safely remove the image item from the scene (if present)
        item_scene = None
        try:
            if hasattr(self, "item") and self.item is not None:
                item_scene = self.item.scene()
        except (AttributeError, RuntimeError):
            item_scene = None

        if item_scene is not None:
            try:
                item_scene.removeItem(self.item)
            except (RuntimeError, AttributeError):
                # If the C++ object has already been deleted, skip removal
                pass

        # Properly end and reset the painter so drawBackground can reinitialize
        self.stop_painter()
        self.current_active_image = None
        self.image = None
        if hasattr(self, "item") and self.item is not None:
            del self.item
        self.item = None
