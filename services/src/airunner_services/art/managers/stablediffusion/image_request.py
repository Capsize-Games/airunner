"""Service-owned image generation request container."""

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from PIL import Image

from airunner_services.contract_enums import (
    DEFAULT_ART_VERSION,
    DEFAULT_IMAGE_GENERATOR,
    GeneratorSection,
)
from airunner_services.settings import AIRUNNER_DEFAULT_SCHEDULER


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
    strength: int = 0.5
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
    controlnet_image: Optional[Image.Image] = None
    controlnet_conditioning_scale: float = 1.0
    control_guidance_start: float = 0.0
    control_guidance_end: float = 1.0
    controlnet_guess_mode: bool = False
    generator_section: GeneratorSection = GeneratorSection.TXT2IMG
    custom_path: Optional[str] = None
    controlnet_enabled: Optional[bool] = None
    controlnet: str = "Canny"
    outpaint_mask_blur: int = 0
    additional_prompts: Optional[List[Dict[str, str]]] = None

    def to_dict(self) -> Dict:
        """Return the request payload as a serializable dictionary."""
        response = {}
        response = asdict(self)
        return response