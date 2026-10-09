"""Utility functions for NSFW safety checking and image marking.

Besides the optional adult-content filter below, this module hosts the
mandatory image-evaluation entry point (:func:`check_images_mandatory`).
The mandatory path always runs its evaluator through the
:mod:`airunner_services.content_safety.image_verdict` seam and has no
enable/disable switch, so disabling the optional filter never disables
it. The mandatory evaluator is the approved Falconsai adapter
(:mod:`airunner_services.content_safety.falconsai`); the SD safety
checker boolean path is superseded for this slot, while the optional
filter keeps its own model and flow.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional, Any

from airunner_services.content_safety import image_verdict
from airunner_services.utils.application.get_logger import get_logger

logger = get_logger(__name__)


def mark_images_as_blocked(
    images: List[Image.Image],
) -> Tuple[List[Image.Image], List[bool]]:
    """Black out every image and flag it as blocked (fail-closed output).

    Used when the output safety filter is enabled but cannot render a
    verdict (model unavailable, or the check raised). Releasing the raw
    image in that state would fail open, so the image is blacked out via
    the same marker used for detections and every flag is ``True`` so
    downstream export/return treats the batch as withheld.

    Args:
        images: List of PIL images to block.

    Returns:
        Tuple of (blocked_images, flags) where flags are all ``True``.
    """
    marked = [_mark_image_as_nsfw(image) for image in images]
    return marked, [True] * len(images)


def check_and_mark_nsfw_images(
    images: List[Image.Image],
    feature_extractor: Optional[Any],
    safety_checker: Optional[Any],
    device: str = "cuda",
    fail_closed: bool = True,
) -> Tuple[List[Image.Image], List[bool]]:
    """Check images for NSFW content and mark detected images.

    Args:
        images: List of PIL images to check
        feature_extractor: Feature extractor model for preprocessing
        safety_checker: Safety checker model for NSFW detection
        device: Device to run inference on ('cuda' or 'cpu')
        fail_closed: When ``True`` (the default), a missing model or a
            raised check blocks the batch instead of releasing raw images.
            Callers that deliberately monitor without enforcing may pass
            ``False`` to keep the legacy pass-through behavior.

    Returns:
        Tuple of (processed_images, nsfw_detected_flags)
        - processed_images: Images with NSFW watermark if detected
        - nsfw_detected_flags: List of booleans indicating NSFW detection

    When ``fail_closed`` is ``True`` and the checker cannot run, every
    image is blacked out and flagged ``True`` so the caller cannot leak
    unchecked output. No prompt or image content is ever logged.
    """
    if not feature_extractor or not safety_checker:
        if fail_closed:
            logger.warning(
                "Content safety filter enabled but the checker model is "
                "unavailable; blocking output (fail closed)"
            )
            return mark_images_as_blocked(images)
        # Monitoring-only mode: return images unchanged with no detections.
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

    except Exception as exc:
        # A raised check is an unknown verdict. When enforcing, block the
        # batch rather than release images that were never inspected.
        # Log only the exception TYPE: a checker's exception message could
        # echo prompt/image payload, which must never reach the logs.
        logger.error(
            "Error during content-safety checking (%s)",
            type(exc).__name__,
        )
        if fail_closed:
            logger.warning(
                "Content safety check could not complete; blocking output "
                "(fail closed)"
            )
            return mark_images_as_blocked(images)
        return images, [False] * len(images)


def check_images_mandatory(
    images: List[Image.Image],
    evaluator: Optional[image_verdict.ImageEvaluator] = None,
) -> Tuple[List[Image.Image], List[bool], image_verdict.ImageBatchVerdict]:
    """Run the MANDATORY image evaluator over one batch.

    There is intentionally no enable/disable switch: disabling the
    optional adult-content filter never disables this path. Evaluator
    resolution is explicit-arg, then registered
    (:func:`image_verdict.get_evaluator`), else unavailable. The
    approved Falconsai adapter
    (:mod:`airunner_services.content_safety.falconsai`) is registered
    on the seam; the SD safety checker boolean path is superseded
    for this slot and no model arguments are accepted here.

    Missing evaluator, raised checks, mismatched batch lengths, and
    uncertain outcomes all withhold (fail closed). Originals are never
    mutated and never written anywhere; withheld outputs are blacked-out
    copies. No automatic export happens here.

    Args:
        images: List of PIL images to check (kept in memory only)
        evaluator: Explicit evaluator, winning over the registered one

    Returns:
        Tuple of (output_images, withheld_flags, batch_verdict).
    """
    resolved = evaluator
    if resolved is None:
        resolved = image_verdict.get_evaluator()
    batch = image_verdict.evaluate_image_batch(images, resolved)
    outputs = [
        image if verdict.allowed else _mark_image_as_nsfw(image, "BLOCKED")
        for image, verdict in zip(list(images), batch.verdicts)
    ]
    return outputs, batch.withheld, batch


def _mark_image_as_nsfw(
    image: Image.Image, label: str = "NSFW"
) -> Image.Image:
    """Mark an image by blacking it out and adding text overlay.

    Args:
        image: PIL Image to mark
        label: Overlay text ('NSFW' for the optional filter, 'BLOCKED'
            for mandatory withholds)

    Returns:
        Marked PIL Image (the input is never mutated)
    """
    # Convert to RGBA for transparency support
    marked = image.convert("RGBA")

    # Black out the entire image
    marked.paste((0, 0, 0), (0, 0, marked.size[0], marked.size[1]))

    # Add text overlay
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
    text = label
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (marked.size[0] - text_width) // 2
    y = (marked.size[1] - text_height) // 2

    # Draw white text
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return marked
