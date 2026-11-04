from typing import Any
from dataclasses import dataclass

from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@dataclass
class ImageToImageRequest:
    input_image: Any
    prompt: str
    strength: float = 0.5


MIN_STRENGTH = 0.0
MAX_STRENGTH = 1.0
DEFAULT_STRENGTH = 0.5


def clamp_strength(value: Any) -> float:
    """Return strength coerced to float and clamped into [0.0, 1.0]."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return DEFAULT_STRENGTH
    return max(MIN_STRENGTH, min(MAX_STRENGTH, number))


def create_image_to_image_request(
    input_image: Any, prompt: str, strength: float = 0.5
) -> ImageToImageRequest:
    """
    Construct an ImageToImageRequest object from parameters.
    Args:
        input_image: The input image (PIL.Image.Image or compatible).
        prompt: The prompt string.
        strength: The strength parameter, clamped into [0.0, 1.0].
    Returns:
        ImageToImageRequest: The constructed request object.
    """
    clamped = clamp_strength(strength)
    logger.debug(
        f"Creating ImageToImageRequest: prompt={prompt}, strength={clamped}"
    )
    return ImageToImageRequest(
        input_image=input_image, prompt=prompt, strength=clamped
    )


def validate_image_to_image_request(request: ImageToImageRequest) -> bool:
    """
    Validate an ImageToImageRequest object for required fields.
    Args:
        request: The ImageToImageRequest to validate.
    Returns:
        bool: True if valid, False otherwise.
    """
    if (
        not request.input_image
        or not request.prompt
        or request.strength is None
    ):
        logger.warning(
            "ImageToImageRequest validation failed: missing input_image, prompt, or strength."
        )
        return False
    try:
        strength = float(request.strength)
    except (TypeError, ValueError):
        return False
    if not MIN_STRENGTH <= strength <= MAX_STRENGTH:
        logger.warning(
            "ImageToImageRequest validation failed: strength out of range."
        )
        return False
    return True
