import os
from typing import Dict, List, Type, Any

import diffusers
from diffusers.pipelines.stable_diffusion_xl.pipeline_stable_diffusion_xl import (
    StableDiffusionXLPipeline,
)
from diffusers.pipelines.stable_diffusion_xl.pipeline_stable_diffusion_xl_img2img import (
    StableDiffusionXLImg2ImgPipeline,
)
from diffusers.pipelines.stable_diffusion_xl.pipeline_stable_diffusion_xl_inpaint import (
    StableDiffusionXLInpaintPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_sd_xl import (
    StableDiffusionXLControlNetPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_sd_xl_img2img import (
    StableDiffusionXLControlNetImg2ImgPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_inpaint_sd_xl import (
    StableDiffusionXLControlNetInpaintPipeline,
)

from compel import ReturnedEmbeddingsType

from airunner.enums import StableDiffusionVersion
from airunner.handlers.stablediffusion.stable_diffusion_model_manager import (
    StableDiffusionModelManager,
)
from airunner.utils.memory import clear_memory


class SDXLModelManager(StableDiffusionModelManager):
    def __init__(self, *args, **kwargs):
        self._refiner = None
        super().__init__(*args, **kwargs)

    @property
    def use_refiner(self) -> bool:
        return self.generator_settings.use_refiner

    @property
    def refiner(self):
        if self._refiner is None:
            cls = self.pipeline_map.get("img2img")
            self._refiner = cls.from_pretrained(
                "stabilityai/stable-diffusion-xl-refiner-1.0",
                text_encoder_2=self._pipe.text_encoder_2,
                vae=self._pipe.vae,
                torch_dtype=self.data_type,
                use_safetensors=True,
                variant="fp16",
            )
            self.unload()
            self._refiner.to("cuda")
        return self._refiner

    @property
    def img2img_pipelines(self):
        return (
            StableDiffusionXLImg2ImgPipeline,
            StableDiffusionXLControlNetImg2ImgPipeline,
        )

    @property
    def txt2img_pipelines(self):
        return (
            StableDiffusionXLPipeline,
            StableDiffusionXLControlNetPipeline,
        )

    @property
    def controlnet_pipelines(self):
        return (
            StableDiffusionXLControlNetPipeline,
            StableDiffusionXLControlNetImg2ImgPipeline,
            StableDiffusionXLControlNetInpaintPipeline,
        )

    @property
    def outpaint_pipelines(self):
        return (
            StableDiffusionXLInpaintPipeline,
            StableDiffusionXLControlNetInpaintPipeline,
        )

    @property
    def is_sd_xl(self) -> bool:
        return self.real_model_version == StableDiffusionVersion.SDXL1_0.value

    @property
    def is_sd_xl_turbo(self) -> bool:
        return (
            self.real_model_version == StableDiffusionVersion.SDXL_TURBO.value
        )

    @property
    def is_sd_xl_or_turbo(self) -> bool:
        return self.is_sd_xl or self.is_sd_xl_turbo

    @property
    def version(self) -> str:
        """
        Turbo paths are SDXL 1.0 paths so we normalize the version to SDXL 1.0
        """
        version = super().version
        if version == "SDXL Turbo":
            version = "SDXL 1.0"
        return version

    @property
    def config_path(self) -> str:
        config_path = super().config_path
        if self.is_sd_xl_turbo:
            config_path = os.path.expanduser(
                os.path.join(
                    self.path_settings_cached.base_path,
                    "art",
                    "models",
                    StableDiffusionVersion.SDXL1_0.value,
                    self.image_request.pipeline_action,
                )
            )
        return config_path

    @property
    def pipeline_map(
        self,
    ) -> Dict[str, Type[diffusers.pipelines.pipeline_utils.DiffusionPipeline]]:
        return {
            "txt2img": StableDiffusionXLPipeline,
            "img2img": StableDiffusionXLImg2ImgPipeline,
            "outpaint": StableDiffusionXLInpaintPipeline,
            "txt2img_controlnet": StableDiffusionXLControlNetPipeline,
            "img2img_controlnet": StableDiffusionXLControlNetImg2ImgPipeline,
            "outpaint_controlnet": StableDiffusionXLControlNetInpaintPipeline,
        }

    @property
    def compel_parameters(self) -> Dict[str, Any]:
        parameters = super().compel_parameters
        parameters["returned_embeddings_type"] = (
            ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED
        )
        parameters["requires_pooled"] = [False, True]
        return parameters

    @property
    def compel_tokenizer(self) -> List[Any]:
        return [self._pipe.tokenizer, self._pipe.tokenizer_2]

    @property
    def compel_text_encoder(self) -> List[Any]:
        return [self._pipe.text_encoder, self._pipe.text_encoder_2]

    def _prepare_compel_data(self, data: Dict) -> Dict:
        data = super()._prepare_compel_data(data)
        data.update(
            {
                "pooled_prompt_embeds": self._pooled_prompt_embeds,
                "negative_pooled_prompt_embeds": self._negative_pooled_prompt_embeds,
            }
        )

        for key in [
            "negative_target_size",
            "negative_original_size",
            "crops_coords_top_left",
        ]:
            val = getattr(self.image_request, key, None)
            if val and val.get("width", None) and val.get("height", None):
                data.update({key: (val["width"], val["height"])})
        return data

    def _build_conditioning_tensors(
        self, compel_prompt, compel_negative_prompt
    ):
        prompt_embeds, pooled_prompt_embeds = (
            self._compel_proc.build_conditioning_tensor(compel_prompt)
        )
        negative_prompt_embeds, negative_pooled_prompt_embeds = (
            self._compel_proc.build_conditioning_tensor(compel_negative_prompt)
        )
        return (
            prompt_embeds,
            pooled_prompt_embeds,
            negative_prompt_embeds,
            negative_pooled_prompt_embeds,
        )

    def _get_results(self, data):
        if self.use_refiner:
            high_noise_frac = 0.7
            image = self._pipe(
                output_type="latent", denoising_end=high_noise_frac, **data
            ).images
            refiner_data = {
                k: v
                for k, v in data.items()
                if k
                not in [
                    "prompt_embeds",
                    "pooled_prompt_embeds",
                    "negative_prompt_embeds",
                    "negative_pooled_prompt_embeds",
                ]
            }
            refiner_data["prompt"] = self.prompt
            refiner_data["negative_prompt"] = self.negative_prompt
            result = self.refiner(
                denoising_start=high_noise_frac, image=image, **refiner_data
            )
            del self._refiner
            self._refiner = None
            clear_memory()
            return result
        return super()._get_results(data)
