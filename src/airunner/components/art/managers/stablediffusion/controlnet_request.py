"""
ControlNet request construction and validation utilities for Stable Diffusion handler.
"""

from typing import Optional, Any
from dataclasses import dataclass

from typing import Optional
from dataclasses import dataclass

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@dataclass
class ControlnetRequest:
    model_path: str
    input_image: Any  # Use PIL.Image.Image or np.ndarray in real code
    conditioning: Optional[str] = None


def create_controlnet_request(
    model_path: str, input_image: Any, conditioning: Optional[str] = None
) -> ControlnetRequest:
    """
    Construct a ControlnetRequest object from parameters.
    Args:
        model_path: Path to the controlnet model file.
        input_image: The input image (PIL.Image.Image or compatible).
        conditioning: Conditioning type (e.g., 'edge', 'depth').
    Returns:
        ControlnetRequest: The constructed request object.
    """
    logger.debug(
        f"Creating ControlnetRequest: model_path={model_path}, conditioning={conditioning}"
    )
    return ControlnetRequest(
        model_path=model_path,
        input_image=input_image,
        conditioning=conditioning,
    )


def validate_controlnet_request(request: ControlnetRequest) -> bool:
    """
    Validate a ControlnetRequest object for required fields.
    Args:
        request: The ControlnetRequest to validate.
    Returns:
        bool: True if valid, False otherwise.
    """
    if not request.model_path or not request.input_image:
        logger.warning(
            "ControlnetRequest validation failed: missing model_path or input_image."
        )
        return False
    return True
