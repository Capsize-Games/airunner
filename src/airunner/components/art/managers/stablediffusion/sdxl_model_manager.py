import os
from typing import Dict, List, Any

from diffusers import (
    StableDiffusionXLPipeline,
    StableDiffusionXLImg2ImgPipeline,
    StableDiffusionXLInpaintPipeline,
    StableDiffusionXLControlNetPipeline,
    StableDiffusionXLControlNetImg2ImgPipeline,
    StableDiffusionXLControlNetInpaintPipeline,
)

from compel import ReturnedEmbeddingsType
from safetensors.torch import load_file

from airunner.components.art.data.embedding import Embedding
from airunner.enums import QualityEffects, StableDiffusionVersion
from airunner.components.art.managers.stablediffusion.stable_diffusion_model_manager import (
    StableDiffusionModelManager,
)
from airunner.utils.memory import clear_memory
from airunner.components.application.managers.base_model_manager import (
    ModelManagerInterface,
)


class BaseDiffusersModelManager:
    pass


class SDXLModelManager(StableDiffusionModelManager, ModelManagerInterface):
    def __init__(self, *args, **kwargs):
        self._refiner = None
        super().__init__(*args, **kwargs)

    @property
    def use_refiner(self) -> bool:
        # return self.generator_settings.use_refiner
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

    def _prepare_data(self, active_rect=None) -> Dict:
        data = super()._prepare_data(active_rect)
        data.update(
            {
                "pooled_prompt_embeds": self._pooled_prompt_embeds,
                "negative_pooled_prompt_embeds": self._negative_pooled_prompt_embeds,
            }
        )

        for key in [
            "crops_coords_top_left",
            "negative_crops_coords_top_left",
        ]:
            val = getattr(self.image_request, key, None)
            if (
                val
                and val.get("x", None) is not None
                and val.get("y", None) is not None
            ):
                data.update({key: (val["x"], val["y"])})

        if (
            self.image_request.quality_effects
            is QualityEffects.HIGH_RESOLUTION
        ):
            data["target_size"] = (
                self.image_request.width,
                self.image_request.height,
            )
            data["original_size"] = (
                self.image_request.width,
                self.image_request.height,
            )
            data["negative_original_size"] = (
                self.image_request.width // 2,
                self.image_request.height // 2,
            )
            data["negative_target_size"] = (
                self.image_request.width // 2,
                self.image_request.height // 2,
            )
        elif (
            self.image_request.quality_effects is QualityEffects.LOW_RESOLUTION
        ):
            data["target_size"] = (
                0,
                0,
            )
            data["original_size"] = (
                0,
                0,
            )
            data["negative_original_size"] = (
                self.image_request.width,
                self.image_request.height,
            )
            data["negative_target_size"] = (
                self.image_request.width,
                self.image_request.height,
            )
        elif self.image_request.quality_effects in (
            QualityEffects.SUPER_SAMPLE_X2,
            QualityEffects.SUPER_SAMPLE_X4,
            QualityEffects.SUPER_SAMPLE_X8,
        ):
            if (
                self.image_request.quality_effects
                is QualityEffects.SUPER_SAMPLE_X2
            ):
                multiplier = 2
            elif (
                self.image_request.quality_effects
                is QualityEffects.SUPER_SAMPLE_X4
            ):
                multiplier = 4
            else:
                multiplier = 8
            data["target_size"] = (
                self.image_request.width,
                self.image_request.height,
            )
            data["original_size"] = (
                self.image_request.width * multiplier,
                self.image_request.height * multiplier,
            )
            data["negative_original_size"] = (
                self.image_request.width // 2,
                self.image_request.height // 2,
            )
            data["negative_target_size"] = (
                self.image_request.width // 2,
                self.image_request.height // 2,
            )
        elif self.image_request.quality_effects is QualityEffects.CUSTOM:
            for key in [
                "target_size",
                "original_size",
                "negative_target_size",
                "negative_original_size",
            ]:
                val = getattr(self.image_request, key, None)
                if (
                    val
                    and val.get("width", None) is not None
                    and val.get("height", None) is not None
                ):
                    data.update({key: (val["width"], val["height"])})

        return data

    def _prepare_lora_data(self, data: Dict) -> Dict:
        if len(self._loaded_lora) > 0:
            self._set_lora_adapters()
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

        # Sanitize and validate prompt inputs
        def _sanitize_prompt(p):
            if not isinstance(p, str):
                return ""
            # Remove problematic characters (e.g., unescaped quotes)
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
            if prompt != "" and second_prompt != "":
                compel_prompt = f'("{prompt}", "{second_prompt}").and()'
            elif prompt != "" and second_prompt == "":
                compel_prompt = prompt
            elif prompt == "" and second_prompt != "":
                compel_prompt = second_prompt
            else:
                compel_prompt = ""

            if negative_prompt != "" and second_negative_prompt != "":
                compel_negative_prompt = (
                    f'("{negative_prompt}", "{second_negative_prompt}").and()'
                )
            elif negative_prompt != "" and second_negative_prompt == "":
                compel_negative_prompt = negative_prompt
            elif negative_prompt == "" and second_negative_prompt != "":
                compel_negative_prompt = second_negative_prompt
            else:
                compel_negative_prompt = ""

            try:
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

            if self._prompt_embeds is not None:
                self._prompt_embeds.half().to(self._device)
            if self._negative_prompt_embeds is not None:
                self._negative_prompt_embeds.half().to(self._device)
            if self._pooled_prompt_embeds is not None:
                self._pooled_prompt_embeds.half().to(self._device)
            if self._negative_pooled_prompt_embeds is not None:
                self._negative_pooled_prompt_embeds.half().to(self._device)

    def _load_embedding(self, embedding: Embedding):
        state_dict = load_file(embedding.path)
        self._pipe.load_textual_inversion(
            state_dict["clip_l"],
            token=embedding.trigger_word.split(","),
            text_encoder=self._pipe.text_encoder,
            tokenizer=self._pipe.tokenizer,
        )
        self._pipe.load_textual_inversion(
            state_dict["clip_g"],
            token=embedding.trigger_word.split(","),
            text_encoder=self._pipe.text_encoder_2,
            tokenizer=self._pipe.tokenizer_2,
        )
        self._loaded_embeddings.append(embedding.path)
        # Invalidate cached prompt embeddings to ensure new embedding is applied
        self._unload_prompt_embeds()

    def _unload_embedding(self, embedding: Embedding):
        self._pipe.unload_textual_inversion(
            tokens=embedding.trigger_word.split(","),
            text_encoder=self._pipe.text_encoder,
            tokenizer=self._pipe.tokenizer,
        )
        self._pipe.unload_textual_inversion(
            tokens=embedding.trigger_word.split(","),
            text_encoder=self._pipe.text_encoder_2,
            tokenizer=self._pipe.tokenizer_2,
        )
        self._loaded_embeddings.remove(embedding.path)
        # Invalidate cached prompt embeddings to ensure embedding removal is applied
        self._unload_prompt_embeds()

    def load_model(self, *args, **kwargs):
        return self._load_model(*args, **kwargs)

    def unload_model(self, *args, **kwargs):
        return self._unload_model(*args, **kwargs)

    def _load_model(self, *args, **kwargs):
        raise NotImplementedError("Implement in subclass or concrete manager.")

    def _unload_model(self, *args, **kwargs):
        raise NotImplementedError("Implement in subclass or concrete manager.")
