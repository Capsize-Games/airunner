"""Utility functions for NSFW safety checking and image marking."""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional, Any


def check_and_mark_nsfw_images(
    images: List[Image.Image],
    feature_extractor: Optional[Any],
    safety_checker: Optional[Any],
    device: str = "cuda",
) -> Tuple[List[Image.Image], List[bool]]:
    """Check images for NSFW content and mark detected images.

    Args:
        images: List of PIL images to check
        feature_extractor: Feature extractor model for preprocessing
        safety_checker: Safety checker model for NSFW detection
        device: Device to run inference on ('cuda' or 'cpu')

    Returns:
        Tuple of (processed_images, nsfw_detected_flags)
        - processed_images: Images with NSFW watermark if detected
        - nsfw_detected_flags: List of booleans indicating NSFW detection
    """
    if not feature_extractor or not safety_checker:
        # If models not loaded, return images unchanged with no detections
        return images, [False] * len(images)

    try:
        # Prepare inputs for safety checker
        safety_checker_input = feature_extractor(
            images, return_tensors="pt"
        ).to(device)

        # Run safety checker
        _, has_nsfw_concepts = safety_checker(
            images=[np.array(img) for img in images],
            clip_input=safety_checker_input.pixel_values.to(device),
        )

        # Mark images with NSFW content
        marked_images = []
        for i, img in enumerate(images):
            if has_nsfw_concepts[i]:
                marked_img = _mark_image_as_nsfw(img)
                marked_images.append(marked_img)
            else:
                marked_images.append(img)

        return marked_images, has_nsfw_concepts

    except Exception as e:
        # On error, return images unchanged
        print(f"Error during NSFW checking: {e}")
        return images, [False] * len(images)


def _mark_image_as_nsfw(image: Image.Image) -> Image.Image:
    """Mark an image as NSFW by blacking it out and adding text overlay.

    Args:
        image: PIL Image to mark

    Returns:
        Marked PIL Image
    """
    # Convert to RGBA for transparency support
    marked = image.convert("RGBA")

    # Black out the entire image
    marked.paste((0, 0, 0), (0, 0, marked.size[0], marked.size[1]))

    # Add "NSFW" text overlay
    draw = ImageDraw.Draw(marked)

    try:
        # Try to load a truetype font
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
        )
    except Exception:
        # Fall back to default font
        font = ImageFont.load_default()

    # Calculate text position (centered)
    text = "NSFW"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (marked.size[0] - text_width) // 2
    y = (marked.size[1] - text_height) // 2

    # Draw white text
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return marked
