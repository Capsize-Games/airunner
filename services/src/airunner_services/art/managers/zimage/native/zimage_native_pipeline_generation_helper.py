"""Generation helpers for the native Z-Image pipeline."""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple, Union

import torch
from PIL import Image

from airunner_services.art.managers.zimage.native.zimage_native_pipeline_sampling_helper import (
    ZImageNativePipelineSamplingHelper,
)


class ZImageNativePipelineGenerationHelper:
    """Handle generation orchestration for the native pipeline."""

    def __init__(self, owner) -> None:
        """Store the owning native pipeline."""
        self._owner = owner
        self._sampling_helper = ZImageNativePipelineSamplingHelper(owner)

    def generate(
        self,
        prompt: Union[str, List[str]],
        negative_prompt: Optional[Union[str, List[str]]] = None,
        height: int = 1024,
        width: int = 1024,
        num_inference_steps: int = 4,
        guidance_scale: float = 0.0,
        num_images_per_prompt: int = 1,
        generator: Optional[torch.Generator] = None,
        latents: Optional[torch.Tensor] = None,
        image: Optional[Any] = None,
        strength: float = 0.8,
        output_type: str = "pil",
        callback: Optional[Callable[[int, torch.Tensor], None]] = None,
        callback_steps: int = 1,
    ) -> Union[torch.Tensor, List[Image.Image]]:
        """Generate images from prompts or an input image."""
        self._validate_generation_inputs(num_inference_steps, image, strength)
        is_img2img = image is not None
        batch_size, prompt_embeds, negative_embeds, attention_mask = (
            self._prepare_prompt_conditioning(
                prompt,
                negative_prompt,
                num_images_per_prompt,
            )
        )
        timesteps = self._sampling_helper.prepare_scheduler_window(
            num_inference_steps,
            is_img2img,
            strength,
        )
        latents = self._sampling_helper.prepare_latents(
            image,
            height,
            width,
            batch_size,
            latents,
            generator,
            timesteps,
            is_img2img,
            strength,
        )
        latents = self._sampling_helper.run_denoising_loop(
            latents,
            timesteps,
            prompt_embeds,
            negative_embeds,
            attention_mask,
            guidance_scale,
            batch_size,
            callback,
            callback_steps,
        )
        return self._sampling_helper.decode_output(latents, output_type)

    def _validate_generation_inputs(
        self,
        num_inference_steps: int,
        image: Optional[Any],
        strength: float,
    ) -> None:
        """Validate components and generation options before sampling."""
        if self._owner.transformer is None:
            raise RuntimeError("Transformer not loaded")
        if self._owner.scheduler is None:
            self._owner.setup_scheduler(num_inference_steps)
        if image is not None and (strength < 0 or strength > 1):
            raise ValueError("Img2img strength must be between 0 and 1")

    def _prepare_prompt_conditioning(
        self,
        prompt: Union[str, List[str]],
        negative_prompt: Optional[Union[str, List[str]]],
        num_images_per_prompt: int,
    ) -> Tuple[
        int,
        torch.Tensor,
        Optional[torch.Tensor],
        Optional[torch.Tensor],
    ]:
        """Prepare prompt embeddings and attention masks for sampling."""
        prompt_helper = self._owner._get_prompt_helper()
        prompt_list = [prompt] if isinstance(prompt, str) else prompt
        batch_size = len(prompt_list) * num_images_per_prompt
        if self._owner.text_encoder is None:
            prompt_embeds = torch.randn(
                batch_size,
                77,
                2560,
                device=self._owner.device,
                dtype=self._owner.dtype,
            )
            return batch_size, prompt_embeds, None, None
        prompt_helper.prepare_text_encoder_for_encoding()
        prompt_embeds, negative_embeds, attention_mask = prompt_helper.encode_prompt(
            prompt_list,
            negative_prompt,
        )
        if num_images_per_prompt > 1:
            prompt_embeds = prompt_embeds.repeat(num_images_per_prompt, 1, 1)
            if negative_embeds is not None:
                negative_embeds = negative_embeds.repeat(
                    num_images_per_prompt,
                    1,
                    1,
                )
            if attention_mask is not None:
                attention_mask = attention_mask.repeat(num_images_per_prompt, 1)
        prompt_embeds, negative_embeds, attention_mask = (
            prompt_helper.move_prompt_conditioning_to_device(
                prompt_embeds,
                negative_embeds,
                attention_mask,
            )
        )
        prompt_helper.release_text_encoder_after_encoding()
        return batch_size, prompt_embeds, negative_embeds, attention_mask
