from typing import Dict
from PIL.Image import Image
from PIL import ImageQt
from PySide6.QtGui import QPainter, QColor, Qt

from airunner.enums import CanvasToolName, SignalCode
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.gui.widgets.canvas.brush_scene import BrushScene


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

    @property
    def current_active_image(self) -> Image:
        if self._is_mask:
            # For mask image (outpainting mask)
            base_64_image = self.drawing_pad_settings.mask
        elif (
            self.settings_key == "controlnet_settings"
            and hasattr(self, "use_generated_image")
            and self.use_generated_image
        ):
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
            image_binary = convert_image_to_binary(image)

            if self._is_mask:
                # For mask image
                self.update_drawing_pad_settings("mask", image_binary)
            elif (
                self.settings_key == "controlnet_settings"
                and hasattr(self, "use_generated_image")
                and self.use_generated_image
            ):
                # For controlnet generated image
                self.update_controlnet_settings(
                    "generated_image", image_binary
                )
            elif self.settings_key == "outpaint_settings":
                # For outpaint image
                self.update_outpaint_settings("image", image_binary)
            elif self.settings_key == "image_to_image_settings":
                # For image-to-image
                self.update_image_to_image_settings("image", image_binary)
            else:
                # Update the appropriate settings
                self._update_current_settings("image", image_binary)

    def _handle_left_mouse_release(self, event) -> bool:
        self.draw_button_down = False

        # Get the correct image based on our settings
        if self.is_brush_or_eraser:
            # Convert image for saving
            image = ImageQt.fromqimage(self.active_image)
            base_64_image = convert_image_to_binary(image)

            # Update based on what type of input image this is
            if self._is_mask:
                # For mask image
                self.update_drawing_pad_settings("mask", base_64_image)
                # Also update the database model
                model = self.drawing_pad_settings.__class__.objects.first()
                model.mask = base_64_image
                model.save()
            elif (
                self.settings_key == "controlnet_settings"
                and hasattr(self, "use_generated_image")
                and self.use_generated_image
            ):
                # For controlnet generated image
                self.update_controlnet_settings(
                    "generated_image", base_64_image
                )
                model = self.controlnet_settings.__class__.objects.first()
                model.generated_image = base_64_image
                model.save()
            elif self.settings_key == "outpaint_settings":
                # For outpaint image
                self.update_outpaint_settings("image", base_64_image)
                model = self.outpaint_settings.__class__.objects.first()
                model.image = base_64_image
                model.save()
            elif self.settings_key == "image_to_image_settings":
                # For image-to-image
                self.update_image_to_image_settings("image", base_64_image)
                model = self.image_to_image_settings.__class__.objects.first()
                model.image = base_64_image
                model.save()

            if self.drawing_pad_settings.enable_automatic_drawing:
                self.api.art.send_request()

        # Clear drawing state
        self._is_drawing = False
        self._is_erasing = False

        return True  # Event handled

    def _handle_image_generated_signal(self, data: Dict):
        if self.current_settings.lock_input_image:
            return
        super()._handle_image_generated_signal(data)
