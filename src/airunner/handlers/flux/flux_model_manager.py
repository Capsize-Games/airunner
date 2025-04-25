import logging
from typing import Any, Dict, Optional
import os
from diffusers import FluxPipeline
import torch

from airunner.enums import (
    EngineResponseCode,
    ModelStatus,
    ModelType,
    SignalCode,
    StableDiffusionVersion,
)
from airunner.handlers.stablediffusion.base_diffusers_model_manager import (
    BaseDiffusersModelManager,
)
from diffusers import (
    FluxPipeline,
    FluxImg2ImgPipeline,
    FluxInpaintPipeline,
    FluxControlNetPipeline,
    FluxControlNetImg2ImgPipeline,
    FluxControlNetInpaintPipeline,
)

from airunner.settings import AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE, CUDA_ERROR
from transformers import (
    CLIPTextModel,
    T5EncoderModel,
    CLIPTokenizer,
    T5TokenizerFast,
)


class FluxModelManager(BaseDiffusersModelManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use None for lazy loading via properties
        self._tokenizer: Optional[CLIPTokenizer] = None
        self._text_encoder: Optional[CLIPTextModel] = None
        self._tokenizer_2: Optional[T5TokenizerFast] = None
        self._text_encoder_2: Optional[T5EncoderModel] = None
        # Assuming self.logger is initialized in the base class
        self.logger.debug("FluxModelManager initialized.")

    @property
    def tokenizer(self) -> CLIPTokenizer:
        if self._tokenizer is None:
            self.logger.debug("Loading CLIPTokenizer")
            # Add local_files_only=True if desired/cached
            # TODO: Make local_files_only configurable or based on settings
            try:
                self._tokenizer = CLIPTokenizer.from_pretrained(
                    "openai/clip-vit-large-patch14", local_files_only=False
                )
            except EnvironmentError:
                self.logger.warning(
                    "Local CLIPTokenizer not found, attempting download."
                )
                self._tokenizer = CLIPTokenizer.from_pretrained(
                    "openai/clip-vit-large-patch14", local_files_only=False
                )
        return self._tokenizer

    @property
    def text_encoder(self) -> CLIPTextModel:
        if self._text_encoder is None:
            self.logger.debug("Loading CLIPTextModel")
            # TODO: Make local_files_only configurable or based on settings
            try:
                self._text_encoder = CLIPTextModel.from_pretrained(
                    "openai/clip-vit-large-patch14",
                    torch_dtype=self.data_type,  # Use standard data type
                    local_files_only=False,
                    # Consider low_cpu_mem_usage=True
                )
            except EnvironmentError:
                self.logger.warning(
                    "Local CLIPTextModel not found, attempting download."
                )
                self._text_encoder = CLIPTextModel.from_pretrained(
                    "openai/clip-vit-large-patch14",
                    torch_dtype=self.data_type,
                    local_files_only=False,
                )
            # Move to device here OR rely on _move_pipe_to_device
            self._text_encoder.to(self._device)
        return self._text_encoder

    @property
    def tokenizer_2(self) -> T5TokenizerFast:
        if self._tokenizer_2 is None:
            self.logger.debug("Loading T5TokenizerFast")
            # TODO: Make local_files_only configurable or based on settings
            try:
                self._tokenizer_2 = T5TokenizerFast.from_pretrained(
                    "google/t5-v1_1-xxl", local_files_only=False
                )
            except EnvironmentError:
                self.logger.warning(
                    "Local T5TokenizerFast not found, attempting download."
                )
                self._tokenizer_2 = T5TokenizerFast.from_pretrained(
                    "google/t5-v1_1-xxl", local_files_only=False
                )
        return self._tokenizer_2

    @property
    def text_encoder_2(self) -> T5EncoderModel:  # Corrected return type
        if self._text_encoder_2 is None:
            self.logger.debug("Loading T5EncoderModel")
            t5_dtype = (
                torch.bfloat16
                if self._device != torch.device("cpu")
                and torch.cuda.is_bf16_supported()
                else torch.float32
            )
            # TODO: Make local_files_only configurable or based on settings
            try:
                self._text_encoder_2 = T5EncoderModel.from_pretrained(
                    "google/t5-v1_1-xxl",
                    torch_dtype=t5_dtype,  # Use appropriate dtype for T5
                    local_files_only=False,
                    # Consider low_cpu_mem_usage=True
                )
            except EnvironmentError:
                self.logger.warning(
                    "Local T5EncoderModel not found, attempting download."
                )
                self._text_encoder_2 = T5EncoderModel.from_pretrained(
                    "google/t5-v1_1-xxl",
                    torch_dtype=t5_dtype,
                    local_files_only=False,
                )
            # Move to device here OR rely on _move_pipe_to_device
            self._text_encoder_2.to(self._device)
        return self._text_encoder_2

    @property
    def img2img_pipelines(self):
        return (
            FluxImg2ImgPipeline,
            FluxControlNetImg2ImgPipeline,
        )

    @property
    def txt2img_pipelines(self):
        return (
            FluxPipeline,
            FluxControlNetPipeline,
        )

    @property
    def outpaint_pipelines(self):
        return (
            FluxInpaintPipeline,
            FluxControlNetInpaintPipeline,
        )

    @property
    def _pipeline_class(self):
        # Determine base pipeline type (can be overridden by specific loaders if needed)
        # ControlNet is handled *after* loading the base pipeline
        if self.is_img2img:
            return FluxImg2ImgPipeline
        elif self.is_outpaint:
            return FluxInpaintPipeline
        else:  # Default to txt2img
            return FluxPipeline

    def _set_pipe(self, config_path: str, data: Dict):
        """Injects Flux-specific components into data for standard loading."""
        self.logger.debug(
            "FluxModelManager: Injecting text components into load data for standard pipeline."
        )
        # Ensure components are loaded via properties before calling base method
        data["tokenizer"] = self.tokenizer
        data["text_encoder"] = (
            self.text_encoder
        )  # Already moved to device in property
        data["tokenizer_2"] = self.tokenizer_2
        data["text_encoder_2"] = (
            self.text_encoder_2
        )  # Already moved to device in property

        # Call the base class method which performs the actual loading
        super()._set_pipe(config_path, data)

    def _load_nf4_flux_pipe(self, model_path: str, data: Dict):
        """Injects text components and calls base NF4 loader placeholder."""
        self.logger.debug(
            "FluxModelManager: Injecting text components into load data for NF4 pipeline."
        )
        # Ensure components are loaded via properties before calling base method
        data["tokenizer"] = self.tokenizer
        data["text_encoder"] = self.text_encoder
        data["tokenizer_2"] = self.tokenizer_2
        data["text_encoder_2"] = self.text_encoder_2

        # Call the base class placeholder (which needs implementation)
        return super()._load_nf4_flux_pipe(model_path, data)
