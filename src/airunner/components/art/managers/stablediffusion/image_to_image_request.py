from typing import Any
from dataclasses import dataclass

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@dataclass
class ImageToImageRequest:
    input_image: Any
    prompt: str
    strength: float = 0.5


def create_image_to_image_request(
    input_image: Any, prompt: str, strength: float = 0.5
) -> ImageToImageRequest:
    """
    Construct an ImageToImageRequest object from parameters.
    Args:
        input_image: The input image (PIL.Image.Image or compatible).
        prompt: The prompt string.
        strength: The strength parameter.
    Returns:
        ImageToImageRequest: The constructed request object.
    """
    logger.debug(
        f"Creating ImageToImageRequest: prompt={prompt}, strength={strength}"
    )
    return ImageToImageRequest(
        input_image=input_image, prompt=prompt, strength=strength
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
    return True
