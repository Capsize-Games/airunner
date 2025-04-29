from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from airunner.settings import AIRUNNER_DEFAULT_SCHEDULER
from airunner.enums import ImagePreset, QualityEffects


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

    additional_prompts: Optional[List[Dict[str, str]]] = None

    def to_dict(self) -> Dict:
        response = {}
        response = asdict(self)
        return response
