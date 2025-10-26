"""
Pipeline setup mixin for X4UpscaleManager.

This mixin handles pipeline loading, configuration, and memory optimization
for the Stable Diffusion X4 upscaler.
"""

import os
from typing import Any, Dict

import torch
from diffusers import StableDiffusionUpscalePipeline

from airunner.enums import ModelStatus, ModelType
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY


class X4PipelineSetupMixin:
    """Pipeline loading and configuration for X4UpscaleManager."""

    def load(self):
        """Load the X4 upscaler pipeline from disk.

        Loads the StableDiffusionUpscalePipeline with appropriate settings for
        the current device (CUDA or CPU), configures memory optimizations, and
        updates model status.

        Raises:
            Exception: If pipeline loading fails.
        """
        if self.is_loaded():
            return

        self.change_model_status(ModelType.UPSCALER, ModelStatus.LOADING)
        try:
            self.logger.info(
                "Loading x4 upscaler pipeline from %s", self.model_path
            )
            file_directory = os.path.dirname(self.model_path)
            data = self._prepare_pipe_data()

            # Load pipeline (same for CUDA and CPU, but data may differ)
            self._pipe = StableDiffusionUpscalePipeline.from_pretrained(
                file_directory, **data
            )

            self._configure_pipeline()

            # Log pipeline details for debugging
            try:
                dev = getattr(self._pipe, "device", None)
                self.logger.info(
                    "x4 upscaler loaded on device=%s dtype=%s",
                    dev,
                    self.data_type,
                )
            except Exception:
                pass

            self.change_model_status(ModelType.UPSCALER, ModelStatus.LOADED)
        except Exception as exc:
            self._pipe = None
            self.change_model_status(ModelType.UPSCALER, ModelStatus.FAILED)
            self.logger.exception("Failed to load x4 upscaler: %s", exc)
            raise

    def _configure_pipeline(self):
        """Configure pipeline memory optimizations and device placement.

        Applies memory-efficient settings including attention slicing,
        xformers optimization, and CPU offload when available. Moves
        pipeline to the appropriate device.
        """
        if not self._pipe:
            return

        self._make_memory_efficient()

        # Enable attention slicing for memory efficiency
        try:
            if hasattr(self._pipe, "enable_attention_slicing"):
                self._pipe.enable_attention_slicing()
        except Exception:
            pass

        # Enable xformers for better memory and speed
        try:
            if hasattr(
                self._pipe, "enable_xformers_memory_efficient_attention"
            ):
                self._pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass

        # Enable CPU offload to reduce VRAM usage
        try:
            if hasattr(self._pipe, "enable_model_cpu_offload"):
                self._pipe.enable_model_cpu_offload()
        except Exception:
            pass

        # Move pipeline to device
        try:
            self._move_pipe_to_device()
        except Exception:
            pass

    def _prepare_pipe_data(self) -> Dict[str, Any]:
        """Prepare configuration data for pipeline loading.

        Returns:
            Dictionary with torch_dtype, safetensors settings, variant,
            local files flag, and device configuration.
        """
        return {
            "torch_dtype": self.data_type,
            "use_safetensors": True,
            "variant": "fp16",
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            "device": self._device,
        }
