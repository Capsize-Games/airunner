from PIL.Image import Image
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from airunner.settings import AIRUNNER_DEFAULT_SCHEDULER
from airunner.enums import ImagePreset, QualityEffects
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.handlers.stablediffusion.controlnet_request import (
    ControlnetRequest,
)


@dataclass
class ImageToImageRequest:
    image: Optional[Image] = None
    strength: float = 0.5
    image_request: Optional[ImageRequest] = None
    controlnet_request: Optional[ControlnetRequest] = None
