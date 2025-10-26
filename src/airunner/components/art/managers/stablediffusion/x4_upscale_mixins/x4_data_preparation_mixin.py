"""
Data preparation mixin for X4UpscaleManager.

This mixin handles request building, data preparation, and parameter
normalization for upscaling operations.
"""

from typing import Any, Dict, Optional, Union

from PIL import Image

from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)


class X4DataPreparationMixin:
    """Data preparation and validation for X4UpscaleManager."""

    DEFAULT_NUM_STEPS = 30
    DEFAULT_GUIDANCE_SCALE = 7.5
    DEFAULT_NOISE_LEVEL = 20

    def _prepare_data(self, active_rect=None) -> Dict:
        """Prepare data for upscaling operation.

        Calls parent's _prepare_data, then removes width/height/clip_skip
        (not used by upscaler), replaces callback field, and adds
        upscaler-specific parameters.

        Args:
            active_rect: Active rectangle for the operation (optional).

        Returns:
            Dictionary with prepared upscaling parameters.
        """
        data = super()._prepare_data(active_rect)

        # Remove parameters not used by upscaler
        del data["width"]
        del data["height"]
        del data["clip_skip"]

        # Upscaler uses different callback parameter name
        data["callback"] = data["callback_on_step_end"]
        del data["callback_on_step_end"]

        # Add upscaler-specific parameters
        data["guidance_scale"] = self.image_request.scale
        data["noise_level"] = self.DEFAULT_NOISE_LEVEL

        return data

    def _build_request_from_payload(
        self, data: Dict, image: Image.Image
    ) -> ImageRequest:
        """Build ImageRequest from payload data and image.

        Extracts parameters from payload dictionary and generator settings,
        applying defaults where needed, and constructs a complete
        ImageRequest for upscaling.

        Args:
            data: Payload dictionary with request parameters.
            image: Source image to be upscaled.

        Returns:
            Constructed ImageRequest for upscaling operation.
        """
        settings = getattr(self, "generator_settings", None)
        defaults = ImageRequest()

        # Extract prompt parameters
        prompt = data.get("prompt", getattr(settings, "prompt", "")) or ""
        negative_prompt = (
            data.get(
                "negative_prompt", getattr(settings, "negative_prompt", "")
            )
            or ""
        )

        # Extract and validate steps
        steps = getattr(settings, "steps", defaults.steps) or defaults.steps
        try:
            steps = max(1, int(steps))
        except (TypeError, ValueError):
            steps = defaults.steps

        # Extract and normalize guidance scale
        scale_raw = data.get("scale", getattr(settings, "scale", None))
        guidance_scale = self._normalize_guidance_scale(scale_raw)

        # Extract and validate seed
        seed = getattr(settings, "seed", defaults.seed)
        try:
            seed = int(seed)
        except (TypeError, ValueError):
            seed = defaults.seed

        # Extract and normalize strength
        strength_raw = getattr(settings, "strength", 100)
        try:
            strength = (float(strength_raw) or 100) / 100
        except (TypeError, ValueError):
            strength = defaults.strength

        return ImageRequest(
            pipeline_action="upscale_x4",
            generator_name=getattr(
                settings, "generator_name", defaults.generator_name
            ),
            prompt=prompt,
            negative_prompt=negative_prompt,
            random_seed=getattr(settings, "random_seed", defaults.random_seed),
            model_path=getattr(settings, "model_name", defaults.model_path),
            custom_path=getattr(settings, "custom_path", defaults.custom_path),
            scheduler=getattr(settings, "scheduler", defaults.scheduler),
            version=getattr(settings, "version", defaults.version),
            use_compel=getattr(settings, "use_compel", defaults.use_compel),
            steps=steps,
            ddim_eta=getattr(settings, "ddim_eta", defaults.ddim_eta),
            scale=guidance_scale,
            seed=seed,
            strength=strength,
            n_samples=1,
            images_per_batch=1,
            clip_skip=getattr(settings, "clip_skip", defaults.clip_skip),
            width=image.width,
            height=image.height,
        )

    def _build_pipeline_kwargs(
        self,
        image,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
    ) -> Dict[str, Any]:
        """Build keyword arguments for pipeline execution.

        Constructs parameter dictionary for upscaler pipeline, handling
        both single images and image sequences appropriately.

        Args:
            image: Single PIL Image or sequence of PIL Images.
            prompt: Text prompt for upscaling.
            negative_prompt: Negative prompt to avoid certain features.
            steps: Number of inference steps.
            guidance_scale: Guidance scale for generation.
            noise_level: Noise level for upscaling.

        Returns:
            Dictionary of pipeline keyword arguments.
        """
        kwargs = {
            "image": image,
            "num_inference_steps": steps,
            "guidance_scale": guidance_scale,
            "noise_level": noise_level,
        }

        # Handle prompts for single images vs batches
        if prompt:
            kwargs["prompt"] = (
                [prompt] * len(image)
                if self._is_image_sequence(image)
                else prompt
            )

        if negative_prompt:
            kwargs["negative_prompt"] = (
                [negative_prompt] * len(image)
                if self._is_image_sequence(image)
                else negative_prompt
            )

        # Filter out None values
        return {
            key: value for key, value in kwargs.items() if value is not None
        }

    def _normalize_guidance_scale(
        self, value: Optional[Union[int, float]]
    ) -> float:
        """Normalize guidance scale value to valid range.

        Handles None, out-of-range values, and percentage-based inputs
        (values > 20 are divided by 100).

        Args:
            value: Raw guidance scale value.

        Returns:
            Normalized guidance scale as float.
        """
        if value is None:
            return self.DEFAULT_GUIDANCE_SCALE

        try:
            scale_value = float(value)
        except (TypeError, ValueError):
            return self.DEFAULT_GUIDANCE_SCALE

        # Convert percentage to decimal (e.g., 750 -> 7.5)
        if scale_value > 20:
            scale_value /= 100

        # Ensure positive value
        if scale_value <= 0:
            return self.DEFAULT_GUIDANCE_SCALE

        return scale_value
