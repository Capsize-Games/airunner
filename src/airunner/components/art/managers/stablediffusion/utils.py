"""
General utility functions for Stable Diffusion handlers.
Handles image resizing, callbacks, seed setting, and other helpers.
Follows project standards: docstrings, type hints, logging.
"""

from typing import Optional
from PIL.Image import Image
import PIL

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def resize_image(
    image: Image, max_width: int, max_height: int
) -> Optional[Image]:
    """Resize the image to fit within max_width and max_height, maintaining aspect ratio."""
    if image is None:
        return None
    original_width, original_height = image.size
    if original_width <= max_width and original_height <= max_height:
        return image
    aspect_ratio = original_width / original_height
    if aspect_ratio > 1:
        new_width = min(max_width, original_width)
        new_height = int(new_width / aspect_ratio)
    else:
        new_height = min(max_height, original_height)
        new_width = int(new_height * aspect_ratio)
    resized_image = image.resize(
        (new_width, new_height), PIL.Image.Resampling.LANCZOS
    )
    logger.info(f"Resized image to {new_width}x{new_height}")
    return resized_image


# Additional general utilities (callbacks, seed setting, etc.) can be added here.
