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

from compel import ReturnedEmbeddingsType, Compel
import torch
from safetensors.torch import load_file

from airunner.components.art.data.embedding import Embedding
from airunner.components.art.managers.stablediffusion import prompt_utils
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

    @property
    def use_compel_dual_prompts(self) -> bool:
        """Whether we should treat primary and secondary prompts as distinct encoder inputs.

        SDXL has two text encoders. Normally (without pre-computed embeds) diffusers passes
        `prompt` to text_encoder and `prompt_2` to text_encoder_2. Our previous Compel usage
        blended both prompts into a single logical expression and fed both encoders with the
        combined text. This property enables a mode where we construct two *separate* Compel
        embeddings – one per encoder – and then concatenate their hidden states to match the
        shape expected by the UNet (feature-dim concat). The pooled embedding comes only from
        the second encoder, mirroring diffusers' internal SDXL `encode_prompt` behavior.
        """
        return self.use_compel and bool(self.second_prompt)

    def _build_dual_compel_embeddings(
        self,
        prompt: str,
        second_prompt: str,
        negative_prompt: str,
        second_negative_prompt: str,
    ):
        """Build embeddings for SDXL where each encoder gets its own logical prompt.

        We instantiate two Compel processors: one for encoder 1 (no pooled output) and
        one for encoder 2 (requires pooled). We then concatenate their sequence hidden
        states across the feature dimension to produce the final `prompt_embeds` /
        `negative_prompt_embeds` tensors expected by the pipeline. Pooled embeddings
        come only from encoder 2 (positive & negative) consistent with SDXL design.

        If a secondary prompt is missing we mirror diffusers behavior by reusing the
        primary prompt for that encoder.
        """
        # Fallbacks to mirror upstream encode_prompt logic
        if not second_prompt:
            second_prompt = prompt
        if not second_negative_prompt:
            second_negative_prompt = negative_prompt

        # Primary encoder Compel (no pooled output required)
        compel_primary = Compel(
            tokenizer=self._pipe.tokenizer,
            text_encoder=self._pipe.text_encoder,
            returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
            requires_pooled=False,
            textual_inversion_manager=self._textual_inversion_manager,
        )
        # Secondary encoder Compel (pooled output required)
        compel_secondary = Compel(
            tokenizer=self._pipe.tokenizer_2,
            text_encoder=self._pipe.text_encoder_2,
            returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
            requires_pooled=True,
            textual_inversion_manager=self._textual_inversion_manager,
        )

        # Positive prompts
        primary_out = compel_primary.build_conditioning_tensor(prompt)
        primary_embeds, _ = self._normalize_compel_output(primary_out)
        secondary_out = compel_secondary.build_conditioning_tensor(
            second_prompt
        )
        secondary_embeds, pooled_secondary = self._normalize_compel_output(
            secondary_out
        )

        # Negative prompts
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

        # Ensure sequence lengths match before concatenation (should normally be fixed 77)
        if primary_embeds.shape[1] != secondary_embeds.shape[1]:
            # Pad shorter sequence with zeros (rare, but safe guard)
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

        # Pad positive/negative to same seq length if needed (should already match)
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
        """Ensure compel output is always a (embeds, pooled) tuple.

        Some Compel configurations (e.g. requires_pooled=False) return only the
        embeddings tensor. We normalize to a 2-tuple to simplify downstream logic.
        """
        if isinstance(out, (list, tuple)) and len(out) == 2:
            return out[0], out[1]
        # Single tensor case
        return out, None

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

        if not self.use_compel:
            data.update(
                {
                    "prompt_2": self.second_prompt,
                    "negative_prompt_2": self.second_negative_prompt,
                }
            )

        return data

    def _prepare_lora_data(self, data: Dict) -> Dict:
        if len(self._loaded_lora) > 0:
            self._set_lora_adapters()
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
            prompt_utils.get_prompt_preset(self.image_request.image_preset),
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
            self.image_request.second_negative_prompt,
            prompt_utils.get_negative_prompt_preset(
                self.image_request.image_preset
            ),
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
                    # Legacy blended behavior
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

            # Move to device & half precision
            for tensor_attr in [
                "_prompt_embeds",
                "_negative_prompt_embeds",
                "_pooled_prompt_embeds",
                "_negative_pooled_prompt_embeds",
            ]:
                t = getattr(self, tensor_attr)
                if t is not None:
                    setattr(self, tensor_attr, t.half().to(self._device))

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
