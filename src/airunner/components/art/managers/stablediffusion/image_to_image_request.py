from PIL.Image import Image
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from airunner.settings import AIRUNNER_DEFAULT_SCHEDULER
from airunner.enums import ImagePreset, QualityEffects
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.controlnet_request import (
    ControlnetRequest,
)

logger = logging.getLogger(__name__)


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
