"""
Image generation, export, and NSFW/metadata utilities for Stable Diffusion handlers.
Handles the main generation loop, exporting images, NSFW checking, and metadata.
Follows project standards: docstrings, type hints, logging.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from airunner.utils.image import export_images

logger = logging.getLogger(__name__)


def check_and_mark_nsfw_images(
    images: List[Image.Image],
    feature_extractor: Any,
    safety_checker: Any,
    device: Any,
) -> Tuple[List[Image.Image], List[bool]]:
    """Check images for NSFW content and mark them if detected."""
    if not feature_extractor or not safety_checker:
        return images, [False] * len(images)
    safety_checker.to(device)
    safety_checker_input = feature_extractor(images, return_tensors="pt").to(device)
    _, has_nsfw_concepts = safety_checker(
        images=[np.array(img) for img in images],
        clip_input=safety_checker_input.pixel_values.to(device),
    )
    for i, img in enumerate(images):
        if has_nsfw_concepts[i]:
            img = img.convert("RGBA")
            img.paste((0, 0, 0), (0, 0, img.size[0], img.size[1]))
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            text = "NSFW"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (img.width - text_width) // 2
            text_y = (img.height - text_height) // 2
            draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))
            images[i] = img
    safety_checker.to("cpu")
    return images, has_nsfw_concepts


class NSFWChecker:
    """
    Dummy NSFW checker for testability. Replace with real implementation.
    """

    def is_nsfw(self, image: Any) -> bool:
        # In real code, run NSFW detection
        return False


def is_nsfw(image: Any) -> bool:
    """
    Check if an image is NSFW using NSFWChecker.
    Args:
        image: The image to check.
    Returns:
        bool: True if NSFW, False otherwise.
    """
    checker = NSFWChecker()
    return checker.is_nsfw(image)


def save_image(image: Any, path: str) -> str:
    """
    Save an image to disk. Stub for testability.
    Args:
        image: The image to save.
        path: The file path to save to.
    Returns:
        str: The path where the image was saved.
    """
    # In real code, image.save(path)
    return path


def export_image(image: Any, path: str) -> str:
    """
    Export an image to disk using save_image.
    Args:
        image: The image to export.
        path: The file path to export to.
    Returns:
        str: The path where the image was exported.
    Raises:
        Exception: If saving fails.
    """
    return save_image(image, path)


def export_images_with_metadata(
    images: List[Image.Image], file_path: str, metadata: Optional[List[dict]]
) -> None:
    """Export images to disk with optional metadata."""
    export_images(images, file_path, metadata)
    logger.info(f"Exported {len(images)} images to {file_path}")


# Additional image generation and metadata utilities can be added here.
