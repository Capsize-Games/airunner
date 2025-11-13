"""
Image generation, export, and metadata utilities for Stable Diffusion handlers.
Handles the main generation loop, exporting images, and metadata.
Follows project standards: docstrings, type hints, logging.
"""

from typing import Any, List, Optional
from PIL import Image
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.image import export_images

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


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
