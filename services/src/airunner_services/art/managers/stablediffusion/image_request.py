"""Service-owned image generation request container."""

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from PIL import Image

from airunner_common.contract_enums import (
    DEFAULT_ART_VERSION,
    DEFAULT_IMAGE_GENERATOR,
    GeneratorSection,
)
from airunner_common.settings import AIRUNNER_DEFAULT_SCHEDULER


MIN_INFERENCE_STEPS = 1
MAX_INFERENCE_STEPS = 150
MIN_IMAGE_DIMENSION = 128
MAX_IMAGE_DIMENSION = 2048
IMAGE_DIMENSION_MULTIPLE = 8
MIN_N_SAMPLES = 1
MAX_N_SAMPLES = 16
MIN_IMAGES_PER_BATCH = 1
MAX_IMAGES_PER_BATCH = 8
MIN_STRENGTH = 0.0
MAX_STRENGTH = 1.0
#: Hard ceiling on pipeline invocations per request, including infinite mode.
MAX_BATCHES_PER_REQUEST = 32


def clamp_int(value: object, low: int, high: int, default: int) -> int:
    """Return value coerced to int and clamped into [low, high]."""
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def clamp_float(
    value: object, low: float, high: float, default: float
) -> float:
    """Return value coerced to float and clamped into [low, high]."""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def snap_dimension(value: object, default: int) -> int:
    """Return an image dimension clamped and snapped to a multiple of 8."""
    size = clamp_int(
        value, MIN_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION, default
    )
    return max(
        MIN_IMAGE_DIMENSION,
        (size // IMAGE_DIMENSION_MULTIPLE) * IMAGE_DIMENSION_MULTIPLE,
    )


@dataclass
class ImageRequest:
    """Image generation request payload shared by GUI and service code."""

    pipeline_action: str = ""
    generator_name: str = DEFAULT_IMAGE_GENERATOR.value
    prompt: str = ""
    negative_prompt: str = ""
    second_prompt: str = ""
    second_negative_prompt: str = ""
    random_seed: bool = True
    model_path: str = ""
    custom_path: str = ""
    scheduler: str = AIRUNNER_DEFAULT_SCHEDULER
    version: str = DEFAULT_ART_VERSION.value
    use_compel: bool = True
    steps: int = 20
    ddim_eta: float = 0.5
    scale: float = 7.5
    seed: int = 42
    strength: float = 0.5
    n_samples: int = 1
    images_per_batch: int = 1
    generate_infinite_images: bool = False
    clip_skip: int = 0
    crops_coords_top_left: Dict = None
    original_size: Dict = None
    target_size: Dict = None
    negative_original_size: Dict = None
    negative_target_size: Dict = None
    negative_crops_coords_top_left: Dict = None
    width: int = 1024
    height: int = 1024
    callback: Optional[callable] = None
    node_id: Optional[str] = None
    skip_auto_export: bool = False
    image: Optional[Image.Image] = None
    mask: Optional[Image.Image] = None
    generator_section: GeneratorSection = GeneratorSection.TXT2IMG
    custom_path: Optional[str] = None
    outpaint_mask_blur: int = 0
    additional_prompts: Optional[List[Dict[str, str]]] = None

    def __post_init__(self) -> None:
        """Clamp numeric fields so hostile values cannot reach pipelines."""
        self.steps = clamp_int(
            self.steps, MIN_INFERENCE_STEPS, MAX_INFERENCE_STEPS, 20
        )
        self.width = snap_dimension(self.width, 1024)
        self.height = snap_dimension(self.height, 1024)
        self.n_samples = clamp_int(
            self.n_samples, MIN_N_SAMPLES, MAX_N_SAMPLES, 1
        )
        self.images_per_batch = clamp_int(
            self.images_per_batch,
            MIN_IMAGES_PER_BATCH,
            MAX_IMAGES_PER_BATCH,
            1,
        )
        self.strength = clamp_float(
            self.strength, MIN_STRENGTH, MAX_STRENGTH, 0.5
        )

    def to_dict(self) -> Dict:
        """Return the request payload as a serializable dictionary."""
        response = {}
        response = asdict(self)
        return response