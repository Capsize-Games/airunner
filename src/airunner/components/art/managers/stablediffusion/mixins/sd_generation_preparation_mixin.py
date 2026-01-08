"""
Mixin providing generation data preparation for Stable Diffusion.

This mixin handles preparing all parameters and data for image generation
including prompts, images, masks, controlnet, and scheduler-specific setup.
"""

from typing import Any, Dict, Optional

import PIL
from PIL.Image import Image

from airunner.components.art.managers.stablediffusion.noise_sampler import (
    DeterministicSDENoiseSampler,
)
from airunner.settings import AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG
from airunner.utils.image import convert_image_to_binary


class SDGenerationPreparationMixin:
    """Mixin providing generation data preparation for Stable Diffusion."""

    def _build_conditioning_tensors(
        self, compel_prompt, compel_negative_prompt
    ):
        """
        Build conditioning tensors using Compel for weighted prompts.

        Args:
            compel_prompt: Prompt string with compel syntax.
            compel_negative_prompt: Negative prompt with compel syntax.

        Returns:
            Tuple of (prompt_embeds, pooled_embeds, negative_embeds, negative_pooled).
        """
        prompt_embeds = self._compel_proc.build_conditioning_tensor(
            compel_prompt
        )
        negative_prompt_embeds = self._compel_proc.build_conditioning_tensor(
            compel_negative_prompt
        )
        return prompt_embeds, None, negative_prompt_embeds, None

    def _prepare_compel_data(self, data: Dict) -> Dict:
        """
        Add Compel prompt embeddings to generation data.

        Args:
            data: Generation parameters dictionary.

        Returns:
            Updated data dictionary with prompt embeddings.
        """
        data.update(
            {
                "prompt_embeds": self._prompt_embeds,
                "negative_prompt_embeds": self._negative_prompt_embeds,
            }
        )
        return data

    def _prepare_data(self, active_rect=None) -> Dict:
        """
        Prepare all parameters for Stable Diffusion generation.

        Args:
            active_rect: Active canvas rectangle for outpainting.

        Returns:
            Dictionary of generation parameters for pipeline.

        Handles txt2img, img2img, inpaint, outpaint, and controlnet modes.
        """
        self.logger.debug("Preparing data")
        self._set_seed()

        data = {
            "width": int(self.image_request.width),
            "height": int(self.image_request.height),
            "clip_skip": int(self.image_request.clip_skip),
            "num_inference_steps": int(self.image_request.steps),
            "callback_on_step_end": self._interrupt_callback,
            "generator": self.generator,
            # Use 1 as default if images_per_batch is None
            "num_images_per_prompt": (
                int(self.image_request.images_per_batch)
                if self.image_request.images_per_batch is not None
                else 1
            ),
        }

        if len(self._loaded_lora) > 0:
            data["cross_attention_kwargs"] = {"scale": self.lora_scale}
            self._set_lora_adapters()

        if self.use_compel:
            data = self._prepare_compel_data(data)

        else:
            data.update(
                {
                    "prompt": self.prompt,
                    "negative_prompt": self.negative_prompt,
                }
            )

        width = int(self.image_request.width)
        height = int(self.image_request.height)
        image = None
        mask = None

        if self.is_txt2img or self.is_outpaint or self.is_img2img:
            data.update({"width": width, "height": height})

        if self.is_img2img:
            # Use image from image_request if available (passed from GUI),
            # otherwise fall back to img2img_image property
            image = self.image_request.image if self.image_request.image is not None else self.img2img_image
            if (
                data["num_inference_steps"]
                < AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG
            ):
                data["num_inference_steps"] = (
                    AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG
                )
        elif self.is_inpaint:
            image = self.img2img_image_cached or self.drawing_pad_image
            mask = self.drawing_pad_mask
            if not image:
                raise ValueError("No image provided for inpainting")
            if not mask:
                raise ValueError("No mask provided for inpainting")
        elif self.is_outpaint:
            image = self.outpaint_image
            if not image:
                image = self.drawing_pad_image
            mask = self.drawing_pad_mask

            # Crop the image based on the active grid location
            active_grid_x = active_rect.left()
            active_grid_y = active_rect.top()
            cropped_image = image.crop(
                (
                    active_grid_x,
                    active_grid_y,
                    width + active_grid_x,
                    height + active_grid_y,
                )
            )

            # Create a new image with a black strip at the bottom
            new_image = PIL.Image.new("RGBA", (width, height), (0, 0, 0, 255))
            new_image.paste(cropped_image, (0, 0))
            image = new_image.convert("RGB")
        elif self.image_request.image is not None:
            image = self.image_request.image

        data["guidance_scale"] = self.image_request.scale

        # set the image to controlnet image if controlnet is enabled
        if self.controlnet_enabled:
            controlnet_image = self.controlnet_image
            if controlnet_image:
                controlnet_image = self._resize_image(
                    controlnet_image, width, height
                )
                control_image = self._controlnet_processor(
                    controlnet_image,
                    to_pil=True,
                    image_resolution=min(width, height),
                    detect_resolution=min(width, height),
                )
                if control_image is not None:
                    self.update_controlnet_settings(
                        generated_image=convert_image_to_binary(control_image),
                    )
                    if self.is_txt2img:
                        image = control_image
                    else:
                        data["control_image"] = control_image
                else:
                    raise ValueError("Controlnet image is None")

        if image is not None:
            image = self._resize_image(image, width, height)
            data["image"] = image

        if mask is not None and (self.is_outpaint or self.is_inpaint):
            mask = self._resize_image(mask, width, height)
            if self.is_outpaint:
                mask = self._pipe.mask_processor.blur(
                    mask, blur_factor=self.mask_blur
                )
            data["mask_image"] = mask

        # DEBUG: Log strength value from image_request
        self.logger.debug(
            "[PREPARE_DATA DEBUG] image_request.strength=%s, is_img2img=%s",
            self.image_request.strength, getattr(self, "is_img2img", False)
        )
        data.update(
            {
                "strength": self.image_request.strength,
            }
        )

        if self.controlnet_enabled:
            data.update(
                {
                    "guess_mode": self.image_request.controlnet_guess_mode,
                    "control_guidance_start": self.image_request.control_guidance_start,
                    "control_guidance_end": self.image_request.control_guidance_end,
                    "guidance_scale": self.image_request.scale,
                    "controlnet_conditioning_scale": self.image_request.controlnet_conditioning_scale,
                }
            )

        # Prepare deterministic noise for SDE schedulers
        data = self._prepare_sde_noise_sampler(data)

        return data

    @staticmethod
    def _resize_image(
        image: Image, max_width: int, max_height: int
    ) -> Optional[Image]:
        """
        Resize image to fit within max dimensions while maintaining aspect ratio.

        Args:
            image: Input PIL Image.
            max_width: Maximum allowed width.
            max_height: Maximum allowed height.

        Returns:
            Resized PIL Image or original if already within bounds.
        """
        if image is None:
            return None

        # Get the original dimensions
        original_width, original_height = image.size

        # Check if resizing is necessary
        if original_width <= max_width and original_height <= max_height:
            return image

        # Calculate the aspect ratio
        aspect_ratio = original_width / original_height

        # Determine the new dimensions while maintaining the aspect ratio
        if aspect_ratio > 1:
            # Landscape orientation
            new_width = min(max_width, original_width)
            new_height = int(new_width / aspect_ratio)
        else:
            # Portrait orientation or square
            new_height = min(max_height, original_height)
            new_width = int(new_height * aspect_ratio)

        # Resize the image
        resized_image = image.resize(
            (new_width, new_height), PIL.Image.Resampling.LANCZOS
        )
        return resized_image

    def _is_sde_scheduler(self) -> bool:
        """
        Check if current scheduler is an SDE variant.

        Returns:
            True if scheduler uses SDE algorithm.
        """
        if not self._pipe or not hasattr(self._pipe, "scheduler"):
            return False

        scheduler = self._pipe.scheduler
        if not hasattr(scheduler, "config"):
            return False

        algorithm_type = getattr(scheduler.config, "algorithm_type", "")
        return "sde" in algorithm_type.lower()

    def _prepare_sde_noise_sampler(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare deterministic noise sampler for SDE schedulers.

        Args:
            data: Generation parameters dictionary.

        Returns:
            Updated data with noise_sampler if using SDE scheduler.

        For DPM++ SDE and similar schedulers, ensures deterministic noise
        generation across batch sizes, matching AUTOMATIC1111's approach.
        """
        if not self._is_sde_scheduler():
            return data

        # Check if determinism is enabled in settings
        if not getattr(
            self.application_settings, "enable_sde_determinism", True
        ):
            return data

        # Get the seed for this generation
        seed = self.image_request.seed

        # Create deterministic noise sampler
        noise_sampler = DeterministicSDENoiseSampler(
            seed=seed, device=self._device
        )

        # Log that we're using deterministic SDE noise
        self.logger.debug(
            "🎲 Using deterministic SDE noise sampler with seed %s for scheduler %s",
            seed,
            self.scheduler_name,
        )

        # Store in data dict - diffusers may use this if the scheduler supports it
        # Note: This is a best-effort approach; not all diffusers schedulers
        # expose a noise_sampler parameter, but we set it in case they do.
        data["noise_sampler"] = noise_sampler

        return data

    def _set_seed(self):
        """
        Set random seed for deterministic generation.

        Uses seed from current image request.
        """
        seed = self.image_request.seed
        self.generator.manual_seed(seed)
