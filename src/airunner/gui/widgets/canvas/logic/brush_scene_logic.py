"""
Business logic for BrushScene: mask creation, color/pen logic, and image processing.
Decoupled from PySide6 GUI code for testability.
"""

import PIL
from PIL import Image, ImageQt
from typing import Optional


class BrushSceneLogic:
    def __init__(self, application_settings, brush_settings, drawing_pad_settings):
        self.application_settings = application_settings
        self.brush_settings = brush_settings
        self.drawing_pad_settings = drawing_pad_settings

    def create_mask_image(self) -> Image.Image:
        return PIL.Image.new(
            "RGBA",
            (
                self.application_settings.working_width,
                self.application_settings.working_height,
            ),
            (0, 0, 0, 255),
        )

    def adjust_mask_alpha(self, mask: Image.Image) -> Image.Image:
        mask = mask.convert("RGBA")
        r, g, b, alpha = mask.split()

        def adjust_alpha(red, green, blue, alpha):
            if red == 0 and green == 0 and blue == 0:
                return 0
            elif red == 255 and green == 255 and blue == 255:
                return 128
            else:
                return alpha

        new_alpha = [
            adjust_alpha(
                r.getpixel((x, y)),
                g.getpixel((x, y)),
                b.getpixel((x, y)),
                alpha.getpixel((x, y)),
            )
            for y in range(mask.height)
            for x in range(mask.width)
        ]
        alpha.putdata(new_alpha)
        mask.putalpha(alpha)
        return mask

    def display_color(
        self, mask_layer_enabled: bool, color: Optional[str] = None
    ) -> str:
        if mask_layer_enabled:
            return "white"
        return color or self.brush_settings.primary_color

    def eraser_color(self, mask_layer_enabled: bool) -> str:
        if mask_layer_enabled:
            return "black"
        return "transparent"
