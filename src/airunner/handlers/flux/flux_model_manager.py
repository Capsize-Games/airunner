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
from airunner.handlers.base_diffusers_model_manager import (
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
        self._tokenizer: Optional[CLIPTokenizer] = None
        self._text_encoder: Optional[CLIPTextModel] = None
        self._tokenizer_2: Optional[T5TokenizerFast] = None
        self._text_encoder_2: Optional[T5EncoderModel] = None

    @property
    def tokenizer(self) -> CLIPTokenizer:
        if self._tokenizer is None:
            self._tokenizer = CLIPTokenizer.from_pretrained(
                "openai/clip-vit-large-patch14"
            )
        return self._tokenizer

    @property
    def text_encoder(self) -> CLIPTextModel:
        if self._text_encoder is None:
            self._text_encoder = CLIPTextModel.from_pretrained(
                "openai/clip-vit-large-patch14"
            )
        return self._text_encoder

    @property
    def tokenizer_2(self) -> T5TokenizerFast:
        if self._tokenizer_2 is None:
            self._tokenizer_2 = T5TokenizerFast.from_pretrained(
                "google/t5-v1_1-xxl"
            )
        return self._tokenizer_2

    @property
    def text_encoder_2(self) -> T5TokenizerFast:
        if self._text_encoder_2 is None:
            self._text_encoder_2 = T5TokenizerFast.from_pretrained(
                "google/t5-v1_1-xxl", torch_dtype=torch.bfloat16
            )
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
        operation_type = "txt2img"
        if self.is_img2img:
            operation_type = "img2img"
        elif self.is_outpaint:
            operation_type = "outpaint"
        if self.controlnet_enabled:
            operation_type = f"{operation_type}_controlnet"
        pipeline_map = {
            "txt2img": FluxPipeline,
            "img2img": FluxImg2ImgPipeline,
            "outpaint": FluxInpaintPipeline,
            "txt2img_controlnet": FluxControlNetPipeline,
            "img2img_controlnet": FluxControlNetImg2ImgPipeline,
            "outpaint_controlnet": FluxControlNetInpaintPipeline,
        }
        return pipeline_map.get(operation_type)

    def _set_pipe(self, config_path: str, data: Dict):
        data["text_encoder"] = self.text_encoder
        data["text_encoder_2"] = self.text_encoder_2
        super()._set_pipe(
            config_path,
            data,
        )
