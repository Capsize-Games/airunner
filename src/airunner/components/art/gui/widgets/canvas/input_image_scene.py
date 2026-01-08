from typing import Dict
from PIL.Image import Image
from PIL import ImageQt
from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage

from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.components.art.gui.widgets.canvas.brush_scene import BrushScene
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)


class InputImageScene(BrushScene):
    """Scene for handling drawing on input images."""

    def __init__(
        self, canvas_type: str, settings_key: str, is_mask: bool = False
    ):
        super().__init__(canvas_type)
        self._settings_key = settings_key
        self._is_mask = is_mask

    @property
    def settings_key(self):
        return self._settings_key

    def _get_default_image_position(self) -> QPoint:
        """Override to always place images at (0, 0) in input image scenes.
        
        Unlike the main canvas which uses drawing_pad_settings for position,
        input image scenes are small preview panels that should always display
        images starting at the origin.
        
        Returns:
            QPoint at (0, 0).
        """
        return QPoint(0, 0)

    def _update_item_position(
        self, root_point: QPoint, canvas_offset
    ) -> None:
        """Override to always position items at (0, 0) in input image scenes.
        
        Input image scenes are small preview panels that should always display
        images at the origin, ignoring any stored position or canvas offset.
        
        Args:
            root_point: Ignored - always uses (0, 0).
            canvas_offset: Ignored - always uses (0, 0).
        """
        try:
            if self.item is not None:
                old_pos = self.item.pos()
                self.item.setPos(0, 0)
                self.logger.info(f"[POSITION DEBUG] _update_item_position called, old_pos={old_pos}, new_pos={self.item.pos()}")
        except (RuntimeError, AttributeError) as e:
            # Item was deleted or is no longer valid
            self.logger.warning(f"[POSITION DEBUG] _update_item_position failed: {e}")
            pass

    def _create_new_item(self, image: QImage, x: int, y: int) -> None:
        """Override to create items without layer context for input image scenes.
        
        Input image scenes should not read position from drawing_pad_settings,
        so we create LayerImageItem with use_layer_context=False.
        
        Args:
            image: The QImage to display.
            x: X position for the item (always 0 for input scenes).
            y: Y position for the item (always 0 for input scenes).
        """
        # Create item without layer context so it doesn't read position from settings
        self.item = LayerImageItem(image, use_layer_context=False)
        if self.item.scene() is None:
            self.addItem(self.item)
            self.item.setPos(0, 0)  # Always at origin for input image scenes
            self.original_item_positions[self.item] = self.item.pos()

    @property
    def current_active_image(self) -> Image:
        if self._is_mask:
            # For mask image (outpainting mask)
            base_64_image = self.drawing_pad_settings.mask
        elif self.settings_key == "controlnet_settings":
            # For controlnet generated image
            base_64_image = self.controlnet_settings.generated_image
        elif self.settings_key == "outpaint_settings":
            # For outpaint image
            base_64_image = self.outpaint_settings.image
        elif self.settings_key == "image_to_image_settings":
            # For image-to-image
            base_64_image = self.image_to_image_settings.image
        else:
            # Default to drawing pad image
            base_64_image = self.current_settings.image

        try:
            return convert_binary_to_image(base_64_image)
        except Exception:
            return None

    @current_active_image.setter
    def current_active_image(self, image: Image):
        if image is not None:
            # Check lock before persisting any changes
            if getattr(self.current_settings, "lock_input_image", False):
                # User has locked the input image; do not persist changes
                return

            image_binary = convert_image_to_binary(image)

            if self._is_mask:
                # For mask image
                self.update_drawing_pad_settings(mask=image_binary)
            elif self.settings_key == "controlnet_settings":
                # For controlnet generated image
                self.update_controlnet_settings(generated_image=image_binary)
            elif self.settings_key == "outpaint_settings":
                # For outpaint image
                self.update_outpaint_settings(image=image_binary)
            elif self.settings_key == "image_to_image_settings":
                # For image-to-image
                self.update_image_to_image_settings(image=image_binary)
            else:
                # Update the appropriate settings
                self._update_current_settings("image", image_binary)

    def _handle_left_mouse_release(self, event) -> bool:
        self.draw_button_down = False

        # Get the correct image based on our settings
        if self.is_brush_or_eraser:
            # Check lock before persisting brush/eraser changes
            if getattr(self.current_settings, "lock_input_image", False):
                # User has locked the input image; do not persist drawing changes
                # Clear drawing state and return
                self._is_drawing = False
                self._is_erasing = False
                return True

            # Convert image for saving
            image = ImageQt.fromqimage(self.active_image)
            base_64_image = convert_image_to_binary(image)

            # Update based on what type of input image this is
            if self._is_mask:
                # For mask image
                self.update_drawing_pad_settings(mask=base_64_image)
                # Also update the database model
                model = self.drawing_pad_settings.__class__.objects.first()
                DrawingPadSettings.objects.update(model.id, mask=base_64_image)
            elif self.settings_key == "controlnet_settings":
                # For controlnet generated image
                self.update_controlnet_settings(generated_image=base_64_image)
                model = self.controlnet_settings.__class__.objects.first()
                ControlnetSettings.objects.update(
                    model.id,
                    generated_image=base_64_image,
                )
            elif self.settings_key == "outpaint_settings":
                # For outpaint image
                self.update_outpaint_settings(image=base_64_image)
                model = self.outpaint_settings.__class__.objects.first()
                OutpaintSettings.objects.update(model.id, image=base_64_image)
            elif self.settings_key == "image_to_image_settings":
                # For image-to-image
                self.update_image_to_image_settings(image=base_64_image)
                model = self.image_to_image_settings.__class__.objects.first()
                ImageToImageSettings.objects.update(
                    model.id, image=base_64_image
                )

            if self.drawing_pad_settings.enable_automatic_drawing:
                self.api.art.send_request()

        # Clear drawing state
        self._is_drawing = False
        self._is_erasing = False

        return True  # Event handled

    def _handle_image_generated_signal(self, data: Dict):
        # Avoid automatically overwriting input images on generation if locked
        if self.current_settings.lock_input_image:
            return
        super()._handle_image_generated_signal(data)
