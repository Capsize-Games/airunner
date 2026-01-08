"""
Mixin providing property accessors for Stable Diffusion model management.

This mixin handles all @property methods for the BaseDiffusersModelManager,
providing access to model configuration, pipeline settings, paths, and state.
"""

import os
from typing import Any, Dict, Optional, Type

import torch
from diffusers import SchedulerMixin
from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    StableDiffusionControlNetPipeline,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionControlNetInpaintPipeline,
    ControlNetModel,
)
from PIL.Image import Image

from airunner.components.art.data.controlnet_model import ControlnetModel
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.rect import Rect
from airunner.components.art.managers.stablediffusion import prompt_utils
from airunner.enums import (
    GeneratorSection,
    ModelStatus,
    ModelType,
    StableDiffusionVersion,
)
from airunner.settings import (
    AIRUNNER_MEM_SD_DEVICE,
)
from airunner.utils.application import get_torch_device


class SDPropertiesMixin:
    """
    Mixin providing property accessors for Stable Diffusion models.

    This mixin contains ~50 @property methods extracted from
    BaseDiffusersModelManager. While large (530 code lines), it's a cohesive
    collection of simple property accessors that are difficult to split further
    without creating overly granular mixins.
    """

    def hardware_profiler(self) -> Any:
        """Get hardware profiler for memory detection.

        Returns:
            Hardware profiler instance for detecting GPU memory and capabilities.
        """
        from airunner.components.art.managers.stablediffusion.memory_utils import (
            get_hardware_profiler,
        )

        return get_hardware_profiler()

    @property
    def active_rect(self) -> Rect:
        """Get active canvas rectangle with drawing pad offset.

        Returns:
            Rect object representing the active generation area.
        """
        pos = self.active_grid_settings.pos
        active_rect = Rect(
            pos[0],
            pos[1],
            self.image_request.width,
            self.image_request.height,
        )
        drawing_pad_pos = self.drawing_pad_settings.pos
        active_rect.translate(
            -drawing_pad_pos[0],
            -drawing_pad_pos[1],
        )
        return active_rect

    @property
    def controlnet(self) -> Optional[ControlNetModel]:
        """Get ControlNet model, loading if necessary.

        Returns:
            Optional ControlNetModel instance.
        """
        if self._controlnet is None:
            self._load_controlnet_model()
        return self._controlnet

    @controlnet.setter
    def controlnet(self, value: Optional[ControlNetModel]):
        """Set ControlNet model.

        Args:
            value: ControlNetModel instance or None to unload.
        """
        if value is None:
            del self._controlnet
        self._controlnet = value

    @property
    def controlnet_processor(self) -> Any:
        """Get ControlNet processor, loading if necessary.

        Returns:
            ControlNet processor instance for image preprocessing.
        """
        if self._controlnet_processor is None:
            self._load_controlnet_processor()
        return self._controlnet_processor

    @controlnet_processor.setter
    def controlnet_processor(self, value: Optional[Any]):
        """Set ControlNet processor.

        Args:
            value: ControlNet processor instance.
        """
        self._controlnet_processor = value

    @property
    def generator(self) -> torch.Generator:
        """Get PyTorch random generator for deterministic generation.

        Returns:
            torch.Generator instance for the current device.
        """
        if self._generator is None:
            self.logger.debug("Loading generator")
            self._generator = torch.Generator(device=self._device)
        return self._generator

    @property
    def controlnet_path(self) -> Optional[str]:
        """Get filesystem path to ControlNet model.

        Returns:
            Optional path string to ControlNet model directory.
        """
        if self.controlnet_model:
            version = self.version
            if version == StableDiffusionVersion.SDXL_TURBO.value:
                version = StableDiffusionVersion.SDXL1_0.value
            return os.path.join(
                self.path_settings.base_path,
                "art/models",
                version,
                "controlnet",
                os.path.expanduser(self.controlnet_model.path),
            )
        return None

    @property
    def controlnet_processor_path(self) -> str:
        """Get filesystem path to ControlNet processor models.

        Returns:
            Path string to ControlNet processor directory.
        """
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art",
                "models",
                "controlnet_processors",
            )
        )

    @property
    def model_status(self) -> Dict[ModelType, ModelStatus]:
        """Get current loading status of all model components.

        Returns:
            Dict mapping ModelType to ModelStatus.
        """
        return self._model_status

    @property
    def img2img_image_cached(self) -> Image:
        """Get cached img2img source image.

        Returns:
            PIL Image for img2img operations.
        """
        if self._img2img_image is None:
            self._img2img_image = self.img2img_image
        return self._img2img_image

    @property
    def image_request(self) -> ImageRequest:
        """Get current image generation request.

        Returns:
            ImageRequest object with generation parameters.
        """
        return self._image_request

    @image_request.setter
    def image_request(self, value: ImageRequest):
        """Set image generation request.

        Args:
            value: ImageRequest object with generation parameters.
        """
        self._image_request = value
        if value is not None:
            pipeline_action = getattr(value, "pipeline_action", None)
            if pipeline_action:
                self._pipeline = pipeline_action
            version = getattr(value, "version", None)
            if version:
                self._resolved_model_version = version

    @property
    def controlnet_image(self) -> Image:
        """Get ControlNet conditioning image.

        Returns:
            PIL Image for ControlNet conditioning.
        """
        return self.image_request.controlnet_image

    @property
    def controlnet_model(self) -> Optional[ControlnetModel]:
        """Get ControlNet model metadata from database.

        Returns:
            Optional ControlnetModel database record.
        """
        if (
            self._controlnet_model is None
            or self._controlnet_model.version != self.version
            or self._controlnet_model.display_name
            != self.image_request.controlnet
        ):
            self.logger.debug(
                f"Loading controlnet model from database {self.image_request.controlnet} {self.version}"
            )
            self._controlnet_model = ControlnetModel.objects.filter_by_first(
                display_name=self.image_request.controlnet,
                version=self.version,
            )
        return self._controlnet_model

    @property
    def controlnet_enabled(self) -> bool:
        """Check if ControlNet is enabled for current generation.

        Returns:
            True if ControlNet should be used.
        """
        if self.image_request:
            controlnet_enabled = self.image_request.controlnet_enabled
            if controlnet_enabled is not None:
                return controlnet_enabled
        return (
            self.controlnet_settings.enabled
            and self.controlnet_settings.image is not None
        )

    @property
    def controlnet_conditioning_scale(self) -> int:
        """Get ControlNet conditioning strength.

        Returns:
            Conditioning scale value (0-100).
        """
        return self.image_request.controlnet_conditioning_scale

    @property
    def controlnet_is_loading(self) -> bool:
        """Check if ControlNet model is currently loading.

        Returns:
            True if ControlNet is being loaded.
        """
        return self.model_status[ModelType.CONTROLNET] is ModelStatus.LOADING

    @property
    def pipeline(self) -> str:
        """Get current pipeline action type.

        Returns:
            Pipeline action string (e.g., 'txt2img', 'img2img').
        """
        return self.image_request.pipeline_action

    @property
    def operation_type(self) -> str:
        """Get operation type including ControlNet suffix if enabled.

        Returns:
            Operation type string (e.g., 'txt2img_controlnet').
        """
        operation_type = self.pipeline
        if self.is_img2img:
            operation_type = "img2img"
        elif self.is_inpaint:
            operation_type = "inpaint"
        elif self.is_outpaint:
            operation_type = "outpaint"
        if self.controlnet_enabled:
            operation_type = f"{operation_type}_controlnet"
        return operation_type

    @property
    def scheduler_name(self) -> str:
        """Get current scheduler name.

        Returns:
            Scheduler name string.
        """
        return self._scheduler_name

    @scheduler_name.setter
    def scheduler_name(self, value: str):
        """Set scheduler name.

        Args:
            value: Scheduler name string.
        """
        self._scheduler_name = value

    @property
    def scheduler(self) -> Type[SchedulerMixin]:
        """Get current scheduler instance.

        Returns:
            Scheduler class instance.
        """
        return self._scheduler

    @scheduler.setter
    def scheduler(self, value: Type[SchedulerMixin]):
        """Set scheduler instance.

        Args:
            value: Scheduler class instance.
        """
        self._scheduler = value

    @property
    def real_model_version(self) -> str:
        """Get the real model version without modifications.

        Only use this when checking the actual version of the model.
        Falls back to generator_settings.version if image_request is not set.

        Returns:
            Model version string.
        """
        if self.image_request is not None:
            return self.image_request.version
        # Fallback to generator_settings when not in generation context
        if self.generator_settings is not None:
            return self.generator_settings.version
        return ""

    @property
    def version(self) -> str:
        """Get model version for current generation.

        Returns:
            Model version string.
        """
        return self.real_model_version

    @property
    def section(self) -> GeneratorSection:
        """Get current generator section.

        Returns:
            GeneratorSection enum value.
        """
        return self.image_request.generator_section

    @property
    def custom_path(self) -> Optional[str]:
        """Get custom model path if specified and exists.

        Returns:
            Optional expanded path string if custom path is valid.
        """
        path_value = self.image_request.custom_path
        if path_value is not None and path_value != "":
            expanded_path = os.path.expanduser(path_value)
            if os.path.exists(expanded_path):
                return expanded_path
        return None

    @property
    def model_path(self) -> Optional[str]:
        """Get model path, prioritizing custom path over default.

        Returns:
            Optional path string to model directory.
        """
        custom_path = self.custom_path
        if custom_path is not None:
            return custom_path

        path = self.image_request.model_path if self.image_request else None

        if path and path != "":
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
            else:
                self.logger.warning(
                    f"Model path specified but does not exist: {path}"
                )

        return None

    @property
    def lora_base_path(self) -> str:
        """Get base path for LoRA models.

        Returns:
            Path string to LoRA model directory.
        """
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
                self.version,
                "lora",
            )
        )

    @property
    def lora_scale(self) -> float:
        """Get LoRA scale as decimal (0.0-1.0).

        Returns:
            LoRA scale value.
        """
        return self.image_request.lora_scale / 100.0

    @property
    def data_type(self) -> torch.dtype:
        """Get appropriate data type based on user settings and hardware.

        Uses the dtype from generator_settings if available, otherwise
        falls back to float16 for CUDA or float32 for CPU.
        
        Note: For quantized modes (4bit, 8bit), this returns the compute dtype
        (bfloat16/float16). The actual quantization is handled separately.

        Returns:
            torch.dtype based on user preference and hardware capability.
        """
        # Get dtype from settings
        dtype_setting = getattr(self.generator_settings, "dtype", None)
        
        # For quantized modes, use bfloat16 as compute dtype
        if dtype_setting in ("4bit", "8bit"):
            if torch.cuda.is_available():
                is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
                if callable(is_bf16_supported) and is_bf16_supported():
                    return torch.bfloat16
                return torch.float16
            return torch.float32
        
        # FP8 support (requires PyTorch 2.1+ and compatible GPU)
        if dtype_setting == "float8":
            if torch.cuda.is_available():
                # FP8 requires Hopper (H100) or Ada Lovelace (RTX 40xx) GPU
                # Use float8_e4m3fn which is optimized for deep learning
                try:
                    # Check if float8 dtype is available
                    if hasattr(torch, "float8_e4m3fn"):
                        return torch.float8_e4m3fn
                except Exception:
                    pass
                # Fallback to bfloat16 if FP8 not available
                is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
                if callable(is_bf16_supported) and is_bf16_supported():
                    return torch.bfloat16
                return torch.float16
            return torch.float32
        
        if dtype_setting == "bfloat16":
            if torch.cuda.is_available():
                is_bf16_supported = getattr(torch.cuda, "is_bf16_supported", None)
                if callable(is_bf16_supported) and is_bf16_supported():
                    return torch.bfloat16
                # Fallback to float16 if bf16 not supported
                return torch.float16
            return torch.float32
        elif dtype_setting == "float16":
            return torch.float16 if torch.cuda.is_available() else torch.float32
        elif dtype_setting == "float32":
            return torch.float32
        
        # Default fallback
        return torch.float16 if torch.cuda.is_available() else torch.float32
    
    @property
    def use_quantization(self) -> bool:
        """Check if quantization should be used based on dtype setting."""
        dtype_setting = getattr(self.generator_settings, "dtype", None)
        return dtype_setting in ("4bit", "8bit")
    
    @property
    def quantization_bits(self) -> Optional[int]:
        """Get quantization bits if quantization is enabled."""
        dtype_setting = getattr(self.generator_settings, "dtype", None)
        if dtype_setting == "4bit":
            return 4
        elif dtype_setting == "8bit":
            return 8
        return None

    @property
    def is_txt2img(self) -> bool:
        """Check if operation is text-to-image.

        Returns:
            True if txt2img mode.
        """
        return self.section is GeneratorSection.TXT2IMG

    @property
    def is_img2img(self) -> bool:
        """Check if operation is image-to-image.

        Returns:
            True if img2img mode.
        """
        return self.section is GeneratorSection.IMG2IMG

    @property
    def is_outpaint(self) -> bool:
        """Check if operation is outpainting.

        Returns:
            True if outpaint mode.
        """
        return self.section is GeneratorSection.OUTPAINT

    @property
    def is_inpaint(self) -> bool:
        """Check if operation is inpainting.

        Returns:
            True if inpaint mode.
        """
        return self.section is GeneratorSection.INPAINT

    @property
    def sd_is_loading(self) -> bool:
        """Check if Stable Diffusion model is currently loading.

        Returns:
            True if SD model is being loaded.
        """
        return self.model_status[self.model_type] is ModelStatus.LOADING

    @property
    def model_is_loaded(self) -> bool:
        """Check if Stable Diffusion model is loaded.

        Returns:
            True if SD model is ready.
        """
        return self.model_status[self.model_type] is ModelStatus.LOADED

    @property
    def sd_is_unloaded(self) -> bool:
        """Check if Stable Diffusion model is unloaded.

        Returns:
            True if SD model is not loaded.
        """
        return self.model_status[self.model_type] is ModelStatus.UNLOADED

    @property
    def _device_index(self):
        """Get GPU device index for Stable Diffusion.

        Returns:
            Device index integer.
        """
        device = AIRUNNER_MEM_SD_DEVICE
        if device is None:
            device = self.memory_settings.default_gpu_sd
        return device

    @property
    def _device(self):
        """Get torch device for Stable Diffusion operations.

        Returns:
            torch.device instance.
        """
        return get_torch_device(self._device_index)

    @property
    def use_from_single_file(self) -> bool:
        """Check if models should be loaded from single file format.

        Returns:
            True to use single-file loading.
        """
        return True

    @property
    def pipeline_map(self) -> Dict[str, Any]:
        """Get mapping of operation types to pipeline classes.

        Returns:
            Dict mapping operation strings to pipeline classes.
        """
        return {
            "txt2img": StableDiffusionPipeline,
            "img2img": StableDiffusionImg2ImgPipeline,
            "inpaint": StableDiffusionInpaintPipeline,
            "outpaint": StableDiffusionInpaintPipeline,
            "txt2img_controlnet": StableDiffusionControlNetPipeline,
            "img2img_controlnet": StableDiffusionControlNetImg2ImgPipeline,
            "inpaint_controlnet": StableDiffusionControlNetInpaintPipeline,
            "outpaint_controlnet": StableDiffusionControlNetInpaintPipeline,
        }

    @property
    def _pipeline_class(self):
        """Get pipeline class for current operation type.

        Returns:
            Pipeline class for current operation.
        """
        return self.pipeline_map.get(self.operation_type)

    @property
    def mask_blur(self) -> int:
        """Get mask blur radius for outpainting.

        Returns:
            Blur radius in pixels.
        """
        return self.image_request.outpaint_mask_blur

    @property
    def do_join_prompts(self) -> bool:
        """Check if additional prompts should be joined.

        Returns:
            True if using compel with additional prompts.
        """
        return (
            self.use_compel
            and self.image_request.additional_prompts is not None
            and len(self.image_request.additional_prompts) > 0
        )

    @property
    def prompt(self) -> str:
        """Get formatted prompt with preset and additional prompts.

        Returns:
            Formatted prompt string.
        """
        prompt = prompt_utils.format_prompt(
            self.image_request.prompt,
            (
                self.image_request.additional_prompts
                if self.do_join_prompts
                else None
            ),
        )
        return prompt

    @property
    def negative_prompt(self) -> str:
        """Get formatted negative prompt with preset.

        Returns:
            Formatted negative prompt string.
        """
        return prompt_utils.format_negative_prompt(
            self.image_request.negative_prompt
        )

    @property
    def config_path(self) -> str:
        """Get path to pipeline configuration directory.

        Returns:
            Path string to config directory.
        """
        path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
                self.version,
                self.pipeline,
            )
        )
        return path

    @property
    def compel_tokenizer(self) -> Any:
        """Get tokenizer from current pipeline for Compel.

        Returns:
            Tokenizer instance.
        """
        return self._pipe.tokenizer

    @property
    def compel_text_encoder(self) -> Any:
        """Get text encoder from current pipeline for Compel.

        Returns:
            Text encoder instance.
        """
        return self._pipe.text_encoder

    @property
    def compel_parameters(self) -> Dict[str, Any]:
        """Get parameters for Compel initialization.

        Returns:
            Dict with compel configuration.
        """
        parameters = {
            "truncate_long_prompts": False,
            "textual_inversion_manager": self._textual_inversion_manager,
            "tokenizer": self.compel_tokenizer,
            "text_encoder": self.compel_text_encoder,
        }
        return parameters
