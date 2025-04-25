from typing import Dict, List, Any, Type

import diffusers
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import (
    StableDiffusionPipeline,
)
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_img2img import (
    StableDiffusionImg2ImgPipeline,
)
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_inpaint import (
    StableDiffusionInpaintPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet import (
    StableDiffusionControlNetPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_img2img import (
    StableDiffusionControlNetImg2ImgPipeline,
)
from diffusers.pipelines.controlnet.pipeline_controlnet_inpaint import (
    StableDiffusionControlNetInpaintPipeline,
)
from airunner.handlers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)


class StableDiffusionModelManager(BaseDiffusersModelManager):
    @property
    def img2img_pipelines(self):
        return (
            StableDiffusionImg2ImgPipeline,
            StableDiffusionControlNetImg2ImgPipeline,
        )

    @property
    def txt2img_pipelines(self):
        return (
            StableDiffusionPipeline,
            StableDiffusionControlNetPipeline,
        )

    @property
    def controlnet_pipelines(self):
        return (
            StableDiffusionControlNetPipeline,
            StableDiffusionControlNetImg2ImgPipeline,
            StableDiffusionControlNetInpaintPipeline,
        )

    @property
    def outpaint_pipelines(self):
        return (
            StableDiffusionInpaintPipeline,
            StableDiffusionControlNetInpaintPipeline,
        )

    @property
    def pipeline_map(
        self,
    ) -> Dict[str, Type[diffusers.pipelines.pipeline_utils.DiffusionPipeline]]:
        return {
            "txt2img": StableDiffusionPipeline,
            "img2img": StableDiffusionImg2ImgPipeline,
            "outpaint": StableDiffusionInpaintPipeline,
            "txt2img_controlnet": StableDiffusionControlNetPipeline,
            "img2img_controlnet": StableDiffusionControlNetImg2ImgPipeline,
            "outpaint_controlnet": StableDiffusionControlNetInpaintPipeline,
        }

    @property
    def _pipeline_class(
        self,
    ) -> Type[diffusers.pipelines.pipeline_utils.DiffusionPipeline]:
        operation_type = "txt2img"
        if self.is_img2img:
            operation_type = "img2img"
        elif self.is_outpaint:
            operation_type = "outpaint"

        if self.controlnet_enabled:
            operation_type = f"{operation_type}_controlnet"

        return self.pipeline_map.get(operation_type)

    @property
    def second_prompt(self) -> str:
        prompt = self.image_request.second_prompt
        prompt_preset = self.prompt_preset

        # Format the prompt
        formatted_prompt = None
        if self.do_join_prompts:
            prompts = [f'"{prompt}"']
            for (
                additional_prompt_settings
            ) in self.image_request.additional_prompts:
                addtional_prompt = additional_prompt_settings[
                    "prompt_secondary"
                ]
                prompts.append(f'"{addtional_prompt}"')
            formatted_prompt = (
                f'({", ".join(prompts)}, "{prompt_preset}").and()'
            )

        if prompt_preset != "":
            prompt = f'("{prompt}", "{prompt_preset}").and()'

        formatted_prompt = formatted_prompt or prompt

        return formatted_prompt

    @property
    def second_negative_prompt(self) -> str:
        prompt = self.image_request.second_negative_prompt
        negative_prompt_preset = self.negative_prompt_preset

        if negative_prompt_preset != "":
            prompt = f'("{prompt}", "{negative_prompt_preset}").and()'

        return prompt

    @property
    def compel_tokenizer(self) -> Any:
        return self._pipe.tokenizer

    @property
    def compel_text_encoder(self) -> Any:
        return self._pipe.text_encoder
