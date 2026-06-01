"""Sampling helpers for the native Z-Image pipeline."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional, Tuple, Union

import torch
from PIL import Image

from airunner_services.art.managers.zimage.native.nextdit_model import (
    ZIMAGE_CONFIG,
)

logger = logging.getLogger(__name__)

class ZImageNativePipelineSamplingHelper:
    """Handle scheduler setup, latent preparation, and decoding."""

    def __init__(self, owner) -> None:
        """Store the owning native pipeline."""
        self._owner = owner

    def prepare_scheduler_window(
        self, num_inference_steps: int, is_img2img: bool, strength: float
    ) -> torch.Tensor:
        """Prepare scheduler timesteps and truncate them for img2img."""
        self._owner.scheduler.set_timesteps(num_inference_steps, device=self._owner.device)
        timesteps = self._owner.scheduler.timesteps
        sigmas = self._owner.scheduler.sigmas
        if is_img2img:
            init_timestep = min(int(num_inference_steps * strength), num_inference_steps)
            init_timestep = max(init_timestep, 1)
            t_start = max(num_inference_steps - init_timestep, 0)
            timesteps = timesteps[t_start:]
            sigmas = sigmas[t_start:]
            if timesteps.numel() == 0 or sigmas.numel() <= 1:
                raise ValueError(
                    "Strength setting removed all timesteps; choose lower "
                    "strength or increase steps."
                )
        self._owner.scheduler.timesteps = timesteps
        self._owner.scheduler.sigmas = sigmas
        if hasattr(self._owner.scheduler, "_step_index"):
            self._owner.scheduler._step_index = 0
        self._owner.scheduler.num_inference_steps = num_inference_steps
        return timesteps

    def prepare_latents(
        self,
        image: Optional[Any],
        height: int,
        width: int,
        batch_size: int,
        latents: Optional[torch.Tensor],
        generator: Optional[torch.Generator],
        timesteps: torch.Tensor,
        is_img2img: bool,
        strength: float,
    ) -> torch.Tensor:
        """Prepare text2img or img2img latents for the denoising loop."""
        vae_helper = self._owner._get_vae_helper()
        if not is_img2img:
            return self._prepare_text2img_latents(
                height,
                width,
                batch_size,
                latents,
                generator,
            )
        if self._owner.vae is None:
            raise RuntimeError("VAE must be loaded for img2img generation")
        vae_helper.ensure_image_processor()
        height, width = self._resolve_image_size(image, height, width)
        vae_helper.ensure_vae_on_device()
        init_image = self._owner.image_processor.preprocess(
            image,
            height=height,
            width=width,
        ).to(device=self._owner.device, dtype=self._owner.vae.dtype)
        image_latents = self._owner.vae.encode(init_image).latent_dist.sample(generator)
        shift_factor = getattr(self._owner.vae.config, "shift_factor", 0.0)
        scaling_factor = getattr(self._owner.vae.config, "scaling_factor", 1.0)
        image_latents = (image_latents - shift_factor) * scaling_factor
        if batch_size > image_latents.shape[0]:
            if batch_size % image_latents.shape[0] != 0:
                raise ValueError(
                    "Cannot duplicate image latents of batch size "
                    f"{image_latents.shape[0]} to {batch_size}"
                )
            repeat_count = batch_size // image_latents.shape[0]
            image_latents = torch.cat([image_latents] * repeat_count, dim=0)
        else:
            image_latents = image_latents[:batch_size]
        image_latents = image_latents.to(device=self._owner.device, dtype=torch.float32)
        if latents is not None:
            return latents.to(device=self._owner.device, dtype=torch.float32)
        noise = self._randn(tuple(image_latents.shape), generator, torch.float32)
        timestep_value = float(timesteps[0].item()) if timesteps.numel() > 0 else 0.0
        timestep_ratio = timestep_value / max(
            self._owner.scheduler.config.num_train_timesteps,
            1,
        )
        logger.debug(
            "[IMG2IMG] strength=%s, first_timestep=%s, timestep_ratio=%.4f",
            strength,
            timestep_value,
            timestep_ratio,
        )
        return (1.0 - timestep_ratio) * image_latents + timestep_ratio * noise

    def _randn(
        self,
        shape: Tuple[int, ...],
        generator: Optional[torch.Generator],
        dtype: torch.dtype = torch.float32,
    ) -> torch.Tensor:
        """Create random noise on the active device with CPU-generator support."""
        if generator is not None and self._owner.device.type == "cuda":
            gen_device = getattr(generator, "device", torch.device("cpu"))
            if getattr(gen_device, "type", "cpu") == "cpu":
                return torch.randn(
                    shape,
                    device="cpu",
                    dtype=dtype,
                    generator=generator,
                ).to(self._owner.device)
        return torch.randn(
            shape,
            device=self._owner.device,
            dtype=dtype,
            generator=generator,
        )

    @staticmethod
    def _resolve_image_size(
        image: Any,
        height: int,
        width: int,
    ) -> Tuple[int, int]:
        """Resolve missing img2img dimensions from the input image."""
        if height is None or width is None:
            if hasattr(image, "height") and hasattr(image, "width"):
                height = height or image.height
                width = width or image.width
            elif isinstance(image, torch.Tensor):
                height = height or int(image.shape[-2])
                width = width or int(image.shape[-1])
        return int(height), int(width)

    def _prepare_text2img_latents(
        self,
        height: int,
        width: int,
        batch_size: int,
        latents: Optional[torch.Tensor],
        generator: Optional[torch.Generator],
    ) -> torch.Tensor:
        """Prepare initial text-to-image latents."""
        latent_channels = ZIMAGE_CONFIG["in_channels"]
        latent_height = height // 8
        latent_width = width // 8
        if latents is None:
            latents = self._randn(
                (batch_size, latent_channels, latent_height, latent_width),
                generator,
                self._owner.dtype,
            )
        else:
            latents = latents.to(device=self._owner.device, dtype=self._owner.dtype)
        if hasattr(self._owner.scheduler, "init_noise_sigma"):
            latents = latents * self._owner.scheduler.init_noise_sigma
        return latents

    def run_denoising_loop(
        self,
        latents: torch.Tensor,
        timesteps: torch.Tensor,
        prompt_embeds: torch.Tensor,
        negative_embeds: Optional[torch.Tensor],
        attention_mask: Optional[torch.Tensor],
        guidance_scale: float,
        batch_size: int,
        callback: Optional[Callable[[int, torch.Tensor], None]],
        callback_steps: int,
    ) -> torch.Tensor:
        """Run the main denoising loop over the prepared timestep window."""
        num_tokens = prompt_embeds.shape[1] if prompt_embeds is not None else 77
        for index, timestep_value in enumerate(timesteps):
            latents = self._run_denoising_step(
                latents,
                timestep_value,
                prompt_embeds,
                negative_embeds,
                attention_mask,
                guidance_scale,
                batch_size,
                num_tokens,
            )
            self._run_callback(
                callback, callback_steps, index, timestep_value, latents
            )
        return latents

    def _run_denoising_step(
        self,
        latents: torch.Tensor,
        timestep_value: torch.Tensor,
        prompt_embeds: torch.Tensor,
        negative_embeds: Optional[torch.Tensor],
        attention_mask: Optional[torch.Tensor],
        guidance_scale: float,
        batch_size: int,
        num_tokens: int,
    ) -> torch.Tensor:
        """Run one denoising step, including CFG and scheduler update."""
        timestep = timestep_value.expand(batch_size)
        timestep = (
            self._owner.scheduler.num_train_timesteps - timestep
        ) / max(self._owner.scheduler.num_train_timesteps, 1)
        if guidance_scale > 1.0 and negative_embeds is not None:
            latent_input = torch.cat([latents, latents], dim=0)
            prompt_input = torch.cat([negative_embeds, prompt_embeds], dim=0)
            timestep_input = timestep.repeat(2)
        else:
            latent_input = latents
            prompt_input = prompt_embeds
            timestep_input = timestep
        noise_pred = self._owner.transformer(
            latent_input,
            timestep_input,
            prompt_input,
            num_tokens=num_tokens,
            attention_mask=attention_mask,
        )
        noise_pred = -noise_pred
        if guidance_scale > 1.0 and negative_embeds is not None:
            noise_pred_neg, noise_pred_pos = noise_pred.chunk(2)
            noise_pred = noise_pred_neg + guidance_scale * (
                noise_pred_pos - noise_pred_neg
            )
        scheduler_output = self._owner.scheduler.step(
            noise_pred.to(torch.float32),
            timestep_value,
            latents.to(torch.float32),
        )
        return (
            scheduler_output.prev_sample
            if hasattr(scheduler_output, "prev_sample")
            else scheduler_output
        )

    def _run_callback(
        self,
        callback: Optional[Callable[[int, torch.Tensor], None]],
        callback_steps: int,
        index: int,
        timestep_value: torch.Tensor,
        latents: torch.Tensor,
    ) -> None:
        """Invoke the optional progress callback for one denoising step."""
        if callback is None or (index + 1) % callback_steps != 0:
            return
        try:
            callback(self._owner, index, timestep_value, {"latents": latents})
        except TypeError:
            callback(index)

    def decode_output(self, latents: torch.Tensor, output_type: str) -> Union[torch.Tensor, List[Image.Image]]:
        """Decode the final latent tensor into the requested output type."""
        vae_helper = self._owner._get_vae_helper()
        if output_type == "latent":
            return latents
        images = latents
        if self._owner.vae is not None:
            vae_helper.ensure_vae_on_device()
            latents = latents / self._owner.vae.config.scaling_factor
            latents = latents.to(
                dtype=self._owner.vae.dtype,
                device=self._owner.device,
            )
            images = self._owner.vae.decode(latents).sample
            images = (images / 2 + 0.5).clamp(0, 1)
        if output_type != "pil":
            return images
        images_np = (
            images.mul(255)
            .clamp(0, 255)
            .to(torch.uint8)
            .permute(0, 2, 3, 1)
            .contiguous()
            .cpu()
            .numpy()
        )
        return [Image.fromarray(image) for image in images_np]