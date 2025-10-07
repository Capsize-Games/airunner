from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from PIL import Image

from airunner.settings import AIRUNNER_DEFAULT_SCHEDULER
from airunner.enums import GeneratorSection, ImagePreset, QualityEffects


@dataclass
class ImageRequest:
    pipeline_action: str = ""
    generator_name: str = "stablediffusion"
    prompt: str = ""
    negative_prompt: str = ""
    second_prompt: str = ""
    second_negative_prompt: str = ""
    random_seed: bool = True
    model_path: str = ""
    custom_path: str = ""
    scheduler: str = AIRUNNER_DEFAULT_SCHEDULER
    version: str = "SD 1.5"
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
    lora_scale: float = 1.0
    width: int = 512
    height: int = 512
    callback: Optional[callable] = None
    image_preset: ImagePreset = ImagePreset.NONE
    quality_effects: QualityEffects = QualityEffects.STANDARD
    node_id: Optional[str] = None
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
    nsfw_filter: Optional[bool] = None
    outpaint_mask_blur: int = 0

    additional_prompts: Optional[List[Dict[str, str]]] = None

    def to_dict(self) -> Dict:
        response = {}
        response = asdict(self)
        return response
