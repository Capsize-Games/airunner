"""
Execution helpers for X4 upscaling.

Contains single-pass execution, pipeline invocation, and alpha compositing
helpers that were previously part of the large core mixin.
"""

from contextlib import nullcontext
from typing import Any

import torch
from PIL import Image


class X4UpscalingExecutionMixin:
    """Pipeline execution helper methods for X4 upscaler."""

    def _single_pass_upscale(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        noise_level: int,
    ) -> Image.Image:
        """Upscale image in single pass through pipeline."""
        kwargs = self._build_pipeline_kwargs(
            image=image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            noise_level=noise_level,
        )

        # Add interrupt callback if available
        interrupt_cb = getattr(
            self, "_BaseDiffusersModelManager__interrupt_callback", None
        )
        if interrupt_cb is not None:
            kwargs["callback"] = interrupt_cb
            kwargs.setdefault("callback_steps", 1)

        images = self._execute_pipe_and_extract(kwargs)
        final_image = images[0]

        # Composite alpha over white background and emit final progress
        final_image = self._composite_alpha(final_image)
        self._emit_progress(100, 100)
        return final_image

    def _composite_alpha(self, image: Image.Image) -> Image.Image:
        """Composite alpha channel over white background."""
        try:
            if "A" in image.getbands():
                rgba = image.convert("RGBA")
                bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                return Image.alpha_composite(bg, rgba).convert("RGB")
            else:
                return image.convert("RGB")
        except Exception:
            return image.convert("RGB")

    def _execute_pipe_and_extract(self, kwargs: Any):
        """Run the pipeline with autocast and return extracted images."""
        self._empty_cache()
        autocast_ctx = (
            torch.autocast("cuda", dtype=self.data_type)
            if torch.cuda.is_available()
            else nullcontext()
        )

        with torch.inference_mode():
            with autocast_ctx:
                result = self._pipe(**kwargs)

        return self._extract_images(result)
