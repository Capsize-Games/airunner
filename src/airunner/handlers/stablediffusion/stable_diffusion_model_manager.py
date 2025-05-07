from typing import Dict, Any, Type

from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    StableDiffusionControlNetPipeline,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionControlNetInpaintPipeline,
)
from airunner.handlers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner.handlers.stablediffusion.prompt_weight_bridge import (
    PromptWeightBridge,
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
    ) -> Dict[str, Any]:
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
    ) -> Any:
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

        prompt = PromptWeightBridge.convert(prompt)
        prompt_preset = PromptWeightBridge.convert(prompt_preset)

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
        prompt = PromptWeightBridge.convert(prompt)
        negative_prompt_preset = PromptWeightBridge.convert(
            negative_prompt_preset
        )

        if negative_prompt_preset != "":
            prompt = f'("{prompt}", "{negative_prompt_preset}").and()'

        return prompt

    @property
    def compel_tokenizer(self) -> Any:
        return self._pipe.tokenizer

    @property
    def compel_text_encoder(self) -> Any:
        return self._pipe.text_encoder

    def _load_prompt_embeds(self):
        if not self.use_compel:
            if self._compel_proc is not None:
                self._unload_compel()
            return

        if self._compel_proc is None:
            self.logger.debug(
                "Compel proc is not loading - attempting to load"
            )
            self._load_compel()

        prompt = self.prompt
        negative_prompt = self.negative_prompt

        if (
            self._current_prompt != prompt
            or self._current_negative_prompt != negative_prompt
        ):
            self._current_prompt = prompt
            self._current_negative_prompt = negative_prompt
            self._unload_prompt_embeds()

        if (
            self._prompt_embeds is None
            or self._negative_prompt_embeds is None
            or self._pooled_prompt_embeds is None
            or self._negative_pooled_prompt_embeds is None
        ):
            self.logger.debug("Loading prompt embeds")

            compel_prompt = prompt
            compel_negative_prompt = negative_prompt

            (
                prompt_embeds,
                pooled_prompt_embeds,
                negative_prompt_embeds,
                negative_pooled_prompt_embeds,
            ) = self._build_conditioning_tensors(
                compel_prompt, compel_negative_prompt
            )

            [prompt_embeds, negative_prompt_embeds] = (
                self._compel_proc.pad_conditioning_tensors_to_same_length(
                    [prompt_embeds, negative_prompt_embeds]
                )
            )

            self._prompt_embeds = prompt_embeds
            self._negative_prompt_embeds = negative_prompt_embeds
            self._pooled_prompt_embeds = pooled_prompt_embeds
            self._negative_pooled_prompt_embeds = negative_pooled_prompt_embeds

            if self._prompt_embeds is not None:
                self._prompt_embeds.half().to(self._device)
            if self._negative_prompt_embeds is not None:
                self._negative_prompt_embeds.half().to(self._device)
            if self._pooled_prompt_embeds is not None:
                self._pooled_prompt_embeds.half().to(self._device)
            if self._negative_pooled_prompt_embeds is not None:
                self._negative_pooled_prompt_embeds.half().to(self._device)
