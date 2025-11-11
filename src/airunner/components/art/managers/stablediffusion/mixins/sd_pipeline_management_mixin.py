"""
Mixin providing pipeline management for Stable Diffusion models.

This mixin handles pipeline loading, swapping, unloading, and device management
for the BaseDiffusersModelManager.
"""

import gc
import os
from typing import Dict

import torch
from airunner.enums import GeneratorSection, ModelStatus
from airunner.settings import AIRUNNER_ADD_WATER_MARK
from airunner.utils.memory import clear_memory


class SDPipelineManagementMixin:
    """Mixin providing pipeline management for Stable Diffusion models."""

    def _swap_pipeline(self):
        """
        Swap current pipeline to match operation type.

        Preserves model components while changing pipeline class to support
        different operations (txt2img, img2img, inpaint, controlnet variants).
        """
        pipeline_class_ = self._pipeline_class
        if (
            self._pipe.__class__ is pipeline_class_ or self._pipe is None
        ):  # noqa
            return
        self.logger.info(
            "Swapping pipeline from %s to %s",
            self._pipe.__class__ if self._pipe else "",
            pipeline_class_,
        )
        try:
            self._unload_compel()
            self._unload_deep_cache()
            self._clear_memory_efficient_settings()
            clear_memory()
            original_config = dict(self._pipe.config)
            kwargs = {
                k: getattr(self._pipe, k) for k in original_config.keys()
            }

            if self.controlnet_enabled:
                kwargs["controlnet"] = self.controlnet
            else:
                kwargs.pop("controlnet", None)

            kwargs = {
                k: v
                for k, v in kwargs.items()
                if k
                in [
                    "vae",
                    "text_encoder",
                    "text_encoder_2",
                    "tokenizer",
                    "tokenizer_2",
                    "unet",
                    "controlnet",
                    # NOTE: "scheduler" is intentionally excluded here
                    # We manage the scheduler separately via _load_scheduler()
                    # to ensure scheduler changes persist across pipeline swaps
                    "image_encoder",
                    "force_zeros_for_empty_prompt",
                ]
            }

            self._pipe = self._pipeline_class(**kwargs)
        except Exception as e:
            self.logger.error(f"Error swapping pipeline: {e}")
        finally:
            # Restore the active scheduler after pipeline swap
            if self.scheduler is not None:
                self._pipe.scheduler = self.scheduler
                self.logger.debug(
                    "Restored scheduler '%s' after pipeline swap",
                    self.scheduler_name,
                )
            self._load_compel()
            # DeepCache disabled: incompatible with torch.compile()
            # self._load_deep_cache()
            self._make_memory_efficient()
            self._send_pipeline_loaded_signal()
            self._move_pipe_to_device()

    def _set_pipe(self, config_path: str, data: Dict):
        """
        Load pipeline from model file.

        Args:
            config_path: Path to pipeline configuration directory.
            data: Dictionary of pipeline initialization parameters.
        """
        pipeline_class_ = self._pipeline_class
        self.logger.info(
            f"Loading {pipeline_class_.__class__} from {self.model_path}"
        )
        if self.use_from_single_file:
            self._pipe = pipeline_class_.from_single_file(
                self.model_path,
                config=config_path,
                add_watermarker=AIRUNNER_ADD_WATER_MARK,
                **data,
            )
        else:
            file_directory = os.path.dirname(self.model_path)
            self._pipe = pipeline_class_.from_pretrained(
                file_directory,
                config=config_path,
                **data,
            )

    def _send_pipeline_loaded_signal(self):
        """
        Emit signal when pipeline is loaded.

        Determines pipeline type from loaded class and notifies API.
        """
        pipeline_type = None
        if self._pipe:
            pipeline_class = self._pipe.__class__
            if pipeline_class in self.txt2img_pipelines:
                pipeline_type = GeneratorSection.TXT2IMG
            elif pipeline_class in self.img2img_pipelines:
                pipeline_type = GeneratorSection.IMG2IMG
            elif pipeline_class in self.outpaint_pipelines:
                pipeline_type = GeneratorSection.INPAINT
        if pipeline_type is not None:
            self.api.art.pipeline_loaded(pipeline_type)

    def _move_pipe_to_device(self):
        """
        Move pipeline to GPU device.

        Handles CUDA out-of-memory errors gracefully.
        """
        if self._pipe is not None:
            try:
                self._pipe.to(self._device)
            except torch.OutOfMemoryError as e:
                self.logger.error(f"Failed to load model to device: {e}")
            except RuntimeError as e:
                self.logger.error(f"Failed to load model to device: {e}")

    def _unload_pipe(self):
        """
        Unload pipeline and free GPU memory.

        Explicitly deletes all major pipeline components (unet, vae,
        text_encoder) to ensure memory is released.
        """
        self.logger.debug("Unloading pipe")
        self.change_model_status(self.model_type, ModelStatus.LOADING)
        if self._pipe is not None:
            # Explicitly delete all major components directly
            try:
                if hasattr(self._pipe, "unet") and self._pipe.unet is not None:
                    del self._pipe.unet
                    self._pipe.unet = None
                if hasattr(self._pipe, "vae") and self._pipe.vae is not None:
                    del self._pipe.vae
                    self._pipe.vae = None
                if (
                    hasattr(self._pipe, "text_encoder")
                    and self._pipe.text_encoder is not None
                ):
                    del self._pipe.text_encoder
                    self._pipe.text_encoder = None
                if (
                    hasattr(self._pipe, "text_encoder_2")
                    and self._pipe.text_encoder_2 is not None
                ):
                    del self._pipe.text_encoder_2
                    self._pipe.text_encoder_2 = None

                # Force garbage collection after deleting components
                gc.collect()

            except Exception as e:
                self.logger.warning(f"Error clearing pipeline components: {e}")

            # Delete the pipeline itself
            del self._pipe
        self._pipe = None

        # Force another gc.collect after pipe deletion
        gc.collect()
