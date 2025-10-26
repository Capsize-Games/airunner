"""
Properties mixin for X4UpscaleManager.

This mixin contains all property accessors for the X4 upscale manager including
compel settings, preview paths, pipeline configuration, and loading status.
"""

import os
from typing import Any, Dict

from diffusers import StableDiffusionUpscalePipeline

from airunner.enums import ModelStatus


class X4PropertiesMixin:
    """Properties for X4UpscaleManager configuration and state."""

    @property
    def use_compel(self) -> bool:
        """X4 upscaler does not support Compel prompt weighting.

        Returns:
            Always False for upscaler pipeline.
        """
        return False

    @property
    def preview_dir(self) -> str:
        """Directory for storing upscaled preview images.

        Returns:
            Absolute path to upscaled images directory.
        """
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "art",
            "upscaled",
        )

    @property
    def preview_path(self) -> str:
        """Path to current upscale preview image.

        Returns:
            Full path to preview file.
        """
        return os.path.join(self.preview_dir, self.PREVIEW_FILENAME)

    @property
    def use_from_single_file(self) -> bool:
        """X4 upscaler uses standard diffusers format, not single file.

        Returns:
            Always False for upscaler pipeline.
        """
        return False

    @property
    def pipeline_map(self) -> Dict[str, Any]:
        """Mapping of pipeline names to pipeline classes.

        Returns:
            Dictionary mapping 'x4-upscaler' to StableDiffusionUpscalePipeline.
        """
        return {"x4-upscaler": StableDiffusionUpscalePipeline}

    def is_loaded(self) -> bool:
        """Check if upscaler pipeline is loaded and ready.

        Returns:
            True if pipeline is loaded and status is LOADED.
        """
        return (
            self._pipe is not None and self.model_status == ModelStatus.LOADED
        )
