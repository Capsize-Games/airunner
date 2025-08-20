from typing import Any, Dict

from diffusers import (
    StableDiffusion3Pipeline,
)
from transformers import (
    CLIPTextModelWithProjection,
    T5EncoderModel,
)

from airunner.components.application.managers.base_model_manager import (
    ModelManagerInterface,
)
from airunner.components.art.managers.stablediffusion.stable_diffusion_model_manager import (
    StableDiffusionModelManager,
)
from airunner.enums import StableDiffusionVersion


class SD35ModelManager(StableDiffusionModelManager, ModelManagerInterface):
    @property
    def img2img_pipelines(self):
        return (StableDiffusion3Pipeline,)

    @property
    def txt2img_pipelines(self):
        return (StableDiffusion3Pipeline,)

    @property
    def outpaint_pipelines(self):
        return (StableDiffusion3Pipeline,)

    @property
    def version(self) -> str:
        return StableDiffusionVersion.SD3_5.value

    @property
    def config_path(self) -> str:
        config_path = super().config_path
        return config_path

    @property
    def pipeline_map(
        self,
    ) -> Dict[str, Any]:
        return {
            "txt2img": StableDiffusion3Pipeline,
            "img2img": StableDiffusion3Pipeline,
        }

    def _load_embeddings(self):
        pass

    def _unload_deep_cache(self):
        pass
