"""
input_image_logic.py

Business logic for InputImage widget, decoupled from Qt GUI code.
Handles settings management, image import/delete/load, and signal connection logic.

All functions/classes here are pure and testable without Qt dependencies.
"""

from typing import Any, Optional
from PIL import Image
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)


class InputImageLogic:
    """Pure business logic for InputImage widget."""

    def __init__(
        self,
        settings_key: str,
        use_generated_image: bool = False,
        is_mask: bool = False,
    ):
        self.settings_key = settings_key
        self.use_generated_image = use_generated_image
        self.is_mask = is_mask

    def get_current_settings(self, context: Any) -> Any:
        if self.settings_key == "controlnet_settings":
            return context.controlnet_settings
        elif self.settings_key == "image_to_image_settings":
            return context.image_to_image_settings
        elif self.settings_key == "outpaint_settings":
            return context.outpaint_settings
        elif self.settings_key == "drawing_pad_settings":
            return context.drawing_pad_settings
        raise ValueError(f"Settings not found for key: {self.settings_key}")

    def update_current_settings(self, context: Any, key: str, value: Any) -> None:
        if self.settings_key == "controlnet_settings":
            context.update_controlnet_settings(key, value)
        elif self.settings_key == "image_to_image_settings":
            context.update_image_to_image_settings(key, value)
        elif self.settings_key == "outpaint_settings":
            context.update_outpaint_settings(key, value)
        elif self.settings_key == "drawing_pad_settings":
            context.update_drawing_pad_settings(key, value)
        else:
            raise ValueError(f"Settings not found for key: {self.settings_key}")

    def load_image_from_settings(self, context: Any) -> Optional[Image.Image]:
        if self.settings_key == "outpaint_settings":
            if self.is_mask:
                image = context.drawing_pad_settings.mask
            else:
                image = context.outpaint_settings.image
        else:
            if self.use_generated_image:
                image = self.get_current_settings(context).generated_image
            else:
                image = self.get_current_settings(context).image
        if image is not None:
            return convert_binary_to_image(image)
        return None

    def delete_image(self, context: Any) -> None:
        if self.settings_key == "outpaint_settings" and self.is_mask:
            context.update_drawing_pad_settings("mask", None)
        else:
            self.update_current_settings(context, "image", None)

    def import_image(self, context: Any, file_path: str) -> None:
        image = Image.open(file_path)
        self.update_current_settings(context, "image", convert_image_to_binary(image))

    def should_update_from_grid(self, context: Any, forced: bool = False) -> bool:
        settings = self.get_current_settings(context)
        if not forced and getattr(settings, "lock_input_image", False):
            return False
        if not forced and not getattr(settings, "use_grid_image_as_input", False):
            return False
        return True

    def update_image_from_grid(self, context: Any) -> None:
        self.update_current_settings(
            context, "image", context.drawing_pad_settings.image
        )
