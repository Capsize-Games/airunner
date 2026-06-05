"""Service-owned SDXL model manager."""

import os
from typing import Any, Dict, List

import torch
from compel import Compel, ReturnedEmbeddingsType
from diffusers import (
    StableDiffusionXLControlNetImg2ImgPipeline,
    StableDiffusionXLControlNetInpaintPipeline,
    StableDiffusionXLControlNetPipeline,
    StableDiffusionXLImg2ImgPipeline,
    StableDiffusionXLInpaintPipeline,
    StableDiffusionXLPipeline,
)

from airunner_services.model_management.model_manager_interface import (
    ModelManagerInterface,
)
from airunner_services.art.managers.stablediffusion import prompt_utils
from airunner_services.art.managers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from airunner_services.contract_enums import StableDiffusionVersion
from airunner_services.utils.memory.clear_memory import clear_memory


class SDXLModelManager(BaseDiffusersModelManager, ModelManagerInterface):
    def __init__(self, *args, **kwargs):
        self._refiner = None
        super().__init__(*args, **kwargs)

    @property
    def use_refiner(self) -> bool:
        return False

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
                    self.path_settings.base_path,
                    "art",
                    "models",
                    StableDiffusionVersion.SDXL1_0.value,
                    self.generator_settings.pipeline_action,
                )
            )
        return config_path

    @property
    def pipeline_map(
        self,
    ) -> Dict[str, Any]:
        return {
            "txt2img": StableDiffusionXLPipeline,
            "img2img": StableDiffusionXLImg2ImgPipeline,
            "inpaint": StableDiffusionXLInpaintPipeline,
            "outpaint": StableDiffusionXLInpaintPipeline,
            "txt2img_controlnet": StableDiffusionXLControlNetPipeline,
            "img2img_controlnet": StableDiffusionXLControlNetImg2ImgPipeline,
            "inpaint_controlnet": StableDiffusionXLControlNetInpaintPipeline,
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

    @property
    def use_compel_dual_prompts(self) -> bool:
        return self.use_compel and bool(self.second_prompt)

    @property
    def use_from_single_file(self) -> bool:
        if not self.model_path:
            return False

        model_path_str = str(self.model_path).lower()
        single_file_extensions = (
            ".safetensors",
            ".ckpt",
            ".pt",
            ".bin",
        )
        return model_path_str.endswith(single_file_extensions)

    def _build_dual_compel_embeddings(
        self,
        prompt: str,
        second_prompt: str,
        negative_prompt: str,
        second_negative_prompt: str,
    ):
        if not second_prompt:
            second_prompt = prompt
        if not second_negative_prompt:
            second_negative_prompt = negative_prompt

        compel_primary = Compel(
            tokenizer=self._pipe.tokenizer,
            text_encoder=self._pipe.text_encoder,
            returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
            requires_pooled=False,
        )
        compel_secondary = Compel(
            tokenizer=self._pipe.tokenizer_2,
            text_encoder=self._pipe.text_encoder_2,
            returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
            requires_pooled=True,
        )

        primary_out = compel_primary.build_conditioning_tensor(prompt)
        primary_embeds, _ = self._normalize_compel_output(primary_out)
        secondary_out = compel_secondary.build_conditioning_tensor(
            second_prompt
        )
        secondary_embeds, pooled_secondary = self._normalize_compel_output(
            secondary_out
        )

        neg_primary_out = compel_primary.build_conditioning_tensor(
            negative_prompt
        )
        neg_primary_embeds, _ = self._normalize_compel_output(neg_primary_out)
        neg_secondary_out = compel_secondary.build_conditioning_tensor(
            second_negative_prompt
        )
        neg_secondary_embeds, neg_pooled_secondary = (
            self._normalize_compel_output(neg_secondary_out)
        )

        if primary_embeds.shape[1] != secondary_embeds.shape[1]:
            max_len = max(primary_embeds.shape[1], secondary_embeds.shape[1])

            def _pad(t):
                if t.shape[1] == max_len:
                    return t
                pad_tokens = max_len - t.shape[1]
                return torch.nn.functional.pad(t, (0, 0, 0, pad_tokens))

            primary_embeds = _pad(primary_embeds)
            secondary_embeds = _pad(secondary_embeds)
        if neg_primary_embeds.shape[1] != neg_secondary_embeds.shape[1]:
            max_len = max(
                neg_primary_embeds.shape[1], neg_secondary_embeds.shape[1]
            )

            def _pad(t):
                if t.shape[1] == max_len:
                    return t
                pad_tokens = max_len - t.shape[1]
                return torch.nn.functional.pad(t, (0, 0, 0, pad_tokens))

            neg_primary_embeds = _pad(neg_primary_embeds)
            neg_secondary_embeds = _pad(neg_secondary_embeds)

        prompt_embeds = torch.cat([primary_embeds, secondary_embeds], dim=-1)
        negative_prompt_embeds = torch.cat(
            [neg_primary_embeds, neg_secondary_embeds], dim=-1
        )

        if prompt_embeds.shape[1] != negative_prompt_embeds.shape[1]:
            max_len = max(
                prompt_embeds.shape[1], negative_prompt_embeds.shape[1]
            )

            def _pad_len(t):
                if t.shape[1] == max_len:
                    return t
                return torch.nn.functional.pad(
                    t, (0, 0, 0, max_len - t.shape[1])
                )

            prompt_embeds = _pad_len(prompt_embeds)
            negative_prompt_embeds = _pad_len(negative_prompt_embeds)

        return (
            prompt_embeds,
            pooled_secondary,
            negative_prompt_embeds,
            neg_pooled_secondary,
        )

    @staticmethod
    def _normalize_compel_output(out) -> tuple:
        if isinstance(out, (list, tuple)) and len(out) == 2:
            return out[0], out[1]
        return out, None

    def _prepare_data(self, active_rect=None) -> Dict:
        data = super()._prepare_data(active_rect)
        data.update(
            {
                "pooled_prompt_embeds": self._pooled_prompt_embeds,
                "negative_pooled_prompt_embeds": self._negative_pooled_prompt_embeds,
            }
        )

        if not self.use_compel:
            data.update(
                {
                    "prompt_2": self.second_prompt,
                    "negative_prompt_2": self.second_negative_prompt,
                }
            )

        return data

    def _build_conditioning_tensors(
        self, compel_prompt, compel_negative_prompt
    ):
        prompt_out = self._compel_proc.build_conditioning_tensor(compel_prompt)
        neg_out = self._compel_proc.build_conditioning_tensor(
            compel_negative_prompt
        )
        prompt_embeds, pooled_prompt_embeds = self._normalize_compel_output(
            prompt_out
        )
        negative_prompt_embeds, negative_pooled_prompt_embeds = (
            self._normalize_compel_output(neg_out)
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

    @property
    def second_prompt(self) -> str:
        second_prompt = prompt_utils.format_prompt(
            self.image_request.second_prompt,
            (
                self.image_request.additional_prompts
                if self.do_join_prompts
                else None
            ),
            second_prompt=True,
        )
        return second_prompt

    @property
    def second_negative_prompt(self) -> str:
        return prompt_utils.format_negative_prompt(
            self.image_request.second_negative_prompt
        )

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
        second_prompt = self.second_prompt
        negative_prompt = self.negative_prompt
        second_negative_prompt = self.second_negative_prompt

        def _sanitize_prompt(p):
            if not isinstance(p, str):
                return ""
            return p.replace('"', "'").strip()

        prompt = _sanitize_prompt(prompt)
        second_prompt = _sanitize_prompt(second_prompt)
        negative_prompt = _sanitize_prompt(negative_prompt)
        second_negative_prompt = _sanitize_prompt(second_negative_prompt)

        if (
            self._current_prompt != prompt
            or self._current_prompt_2 != second_prompt
            or self._current_negative_prompt != negative_prompt
            or self._current_negative_prompt_2 != second_negative_prompt
        ):
            self._current_prompt = prompt
            self._current_prompt_2 = second_prompt
            self._current_negative_prompt = negative_prompt
            self._current_negative_prompt_2 = second_negative_prompt
            self._unload_prompt_embeds()

        if (
            self._prompt_embeds is None
            or self._pooled_prompt_embeds is None
            or self._negative_prompt_embeds is None
            or self._negative_pooled_prompt_embeds is None
        ):
            self.logger.debug("Loading prompt embeds")
            try:
                if self.use_compel_dual_prompts:
                    (
                        prompt_embeds,
                        pooled_prompt_embeds,
                        negative_prompt_embeds,
                        negative_pooled_prompt_embeds,
                    ) = self._build_dual_compel_embeddings(
                        prompt,
                        second_prompt,
                        negative_prompt,
                        second_negative_prompt,
                    )
                else:
                    if prompt != "" and second_prompt != "":
                        compel_prompt = (
                            f'("{prompt}", "{second_prompt}").and()'
                        )
                    elif prompt != "" and second_prompt == "":
                        compel_prompt = prompt
                    elif prompt == "" and second_prompt != "":
                        compel_prompt = second_prompt
                    else:
                        compel_prompt = ""

                    if negative_prompt != "" and second_negative_prompt != "":
                        compel_negative_prompt = f'("{negative_prompt}", "{second_negative_prompt}").and()'
                    elif (
                        negative_prompt != "" and second_negative_prompt == ""
                    ):
                        compel_negative_prompt = negative_prompt
                    elif (
                        negative_prompt == "" and second_negative_prompt != ""
                    ):
                        compel_negative_prompt = second_negative_prompt
                    else:
                        compel_negative_prompt = ""

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
            except RuntimeError as e:
                self.logger.error(f"Prompt embedding failed: {e}")
                self._prompt_embeds = None
                self._negative_prompt_embeds = None
                self._pooled_prompt_embeds = None
                self._negative_pooled_prompt_embeds = None
                raise ValueError(
                    "Prompt could not be processed. Please check for invalid or excessively long prompt text."
                ) from e

            self._prompt_embeds = prompt_embeds
            self._negative_prompt_embeds = negative_prompt_embeds
            self._pooled_prompt_embeds = pooled_prompt_embeds
            self._negative_pooled_prompt_embeds = negative_pooled_prompt_embeds

            for tensor_attr in [
                "_prompt_embeds",
                "_negative_prompt_embeds",
                "_pooled_prompt_embeds",
                "_negative_pooled_prompt_embeds",
            ]:
                t = getattr(self, tensor_attr)
                if t is not None:
                    setattr(self, tensor_attr, t.half().to(self._device))

    def load_model(self, *args, **kwargs):
        return self._load_model(*args, **kwargs)

    def unload_model(self, *args, **kwargs):
        return self._unload_model(*args, **kwargs)

    def _load_model(self, *args, **kwargs):
        raise NotImplementedError("Implement in subclass or concrete manager.")

    def _unload_model(self, *args, **kwargs):
        raise NotImplementedError("Implement in subclass or concrete manager.")


__all__ = ["SDXLModelManager"]
