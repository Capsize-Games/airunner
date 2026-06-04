"""
Native Z-Image Pipeline.

This module provides a complete image generation pipeline for Z-Image
without diffusers dependency, supporting FP8 scaled checkpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn

from airunner_services.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)
from airunner_services.art.managers.zimage.native.nextdit_model import (
    NextDiT,
)
from airunner_services.art.managers.zimage.native.zimage_text_encoder import (
    ZImageTextEncoder,
    ZImageTokenizer,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_prompt_helper import (
    ZImageNativePipelinePromptHelper,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_generation_helper import (
    ZImageNativePipelineGenerationHelper,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_transformer_loader_helper import (
    ZImageNativePipelineTransformerLoaderHelper,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_transformer_support import (
    ZImageNativePipelineTransformerSupport,
)
from airunner_services.art.managers.zimage.native.zimage_native_pipeline_vae_helper import (
    NativeVaeImageProcessor,
    ZImageNativePipelineVaeHelper,
)

logger = logging.getLogger(__name__)

class ZImageNativePipeline:
    """
    Native Z-Image pipeline for image generation.
    
    This pipeline handles:
    - FP8 checkpoint loading with streaming
    - Text encoding with Qwen
    - Flow matching sampling
    - VAE decoding
    
    Args:
        transformer_path: Path to transformer checkpoint (FP8 or regular)
        text_encoder_path: Path to text encoder model
        vae_path: Path to VAE model
        device: Target device
        dtype: Compute dtype (bfloat16 recommended)
        text_encoder_quantization: Quantization for text encoder ("4bit", "8bit", None)
    """
    
    def __init__(
        self,
        transformer_path: Optional[str] = None,
        text_encoder_path: Optional[str] = None,
        vae_path: Optional[str] = None,
        device: Optional[torch.device] = None,
        dtype: torch.dtype = torch.bfloat16,
        text_encoder_quantization: Optional[str] = "4bit",
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        elif isinstance(device, str):
            self.device = torch.device(device)
        else:
            self.device = device
        self.dtype = dtype
        self.text_encoder_quantization = text_encoder_quantization
        self.image_processor: Optional[NativeVaeImageProcessor] = None
        
        # Components
        self.transformer: Optional[NextDiT] = None
        self.text_encoder: Optional[ZImageTextEncoder] = None
        self.tokenizer: Optional[ZImageTokenizer] = None
        self.vae: Optional[nn.Module] = None
        self.scheduler: Optional[FlowMatchEulerScheduler] = None
        
        # Paths
        self.transformer_path = transformer_path
        self.text_encoder_path = text_encoder_path
        self.vae_path = vae_path
        
        # State
        self.is_fp8 = False
        self.hf_device_map = None
        self._loaded_components: List[str] = []

    def _get_prompt_helper(self) -> ZImageNativePipelinePromptHelper:
        """Return the cached prompt-conditioning helper."""
        helper = getattr(self, "_prompt_helper", None)
        if helper is None:
            helper = ZImageNativePipelinePromptHelper(self)
            self._prompt_helper = helper
        return helper

    def _get_generation_helper(self) -> ZImageNativePipelineGenerationHelper:
        """Return the cached generation helper."""
        helper = getattr(self, "_generation_helper", None)
        if helper is None:
            helper = ZImageNativePipelineGenerationHelper(self)
            self._generation_helper = helper
        return helper

    def _get_transformer_loader_helper(
        self,
    ) -> ZImageNativePipelineTransformerLoaderHelper:
        """Return the cached transformer loader helper."""
        helper = getattr(self, "_transformer_loader_helper", None)
        if helper is None:
            helper = ZImageNativePipelineTransformerLoaderHelper(self)
            self._transformer_loader_helper = helper
        return helper

    def _get_transformer_support(self) -> ZImageNativePipelineTransformerSupport:
        """Return the cached transformer support helper."""
        helper = getattr(self, "_transformer_support", None)
        if helper is None:
            helper = ZImageNativePipelineTransformerSupport(self)
            self._transformer_support = helper
        return helper

    def _get_vae_helper(self) -> ZImageNativePipelineVaeHelper:
        """Return the cached VAE helper."""
        helper = getattr(self, "_vae_helper", None)
        if helper is None:
            helper = ZImageNativePipelineVaeHelper(self)
            self._vae_helper = helper
        return helper

    @property
    def components(self) -> Dict[str, Any]:
        """Diffusers-style components mapping used by PEFT loaders."""
        comps: Dict[str, Any] = {
            "transformer": self.transformer,
            "text_encoder": self.text_encoder,
            "tokenizer": self.tokenizer,
            "vae": self.vae,
            "scheduler": self.scheduler,
        }
        return {k: v for k, v in comps.items() if v is not None}
    
    @property
    def memory_usage(self) -> Dict[str, float]:
        """Get current memory usage in GB."""
        if not torch.cuda.is_available():
            return {"vram": 0, "cpu": 0}
        
        vram = torch.cuda.memory_allocated() / 1024**3
        cpu = torch.cuda.memory_reserved() / 1024**3  # Approximation

        # PEFT compatibility: diffusers LoRA loader checks hf_device_map
        # even though native pipeline manages devices internally.
        self.hf_device_map = None
        
        return {"vram": vram, "cpu": cpu}
    
    def load_transformer(
        self,
        checkpoint_path: Optional[str] = None,
        stream_load: bool = True,
    ) -> None:
        """Load the transformer from checkpoint."""
        self._get_transformer_loader_helper().load_transformer(
            checkpoint_path,
            stream_load,
        )
    
    def load_text_encoder(
        self,
        model_path: Optional[str] = None,
        tokenizer_path: Optional[str] = None,
        use_4bit: bool = False,
    ) -> None:
        """Load the text encoder."""
        self._get_prompt_helper().load_text_encoder(
            model_path,
            tokenizer_path,
            use_4bit,
        )
    
    def load_vae(
        self,
        vae_path: Optional[str] = None,
    ) -> None:
        """Load the VAE decoder."""
        self._get_vae_helper().load_vae(vae_path)
    
    def setup_scheduler(
        self,
        num_inference_steps: int = 4,
        shift: float = 3.0,
    ) -> None:
        """Set up the flow matching scheduler."""
        self._get_vae_helper().setup_scheduler(num_inference_steps, shift)
    
    def encode_prompt(
        self,
        prompt: Union[str, List[str]],
        negative_prompt: Optional[Union[str, List[str]]] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """Encode text prompt to embeddings."""
        return self._get_prompt_helper().encode_prompt(
            prompt,
            negative_prompt,
        )
    
    @torch.no_grad()
    def generate(
        self,
        prompt: Union[str, List[str]],
        negative_prompt: Optional[Union[str, List[str]]] = None,
        height: int = 1024,
        width: int = 1024,
        num_inference_steps: int = 4,
        guidance_scale: float = 0.0,
        num_images_per_prompt: int = 1,
        generator: Optional[torch.Generator] = None,
        latents: Optional[torch.Tensor] = None,
        image: Optional[Any] = None,
        strength: float = 0.8,
        output_type: str = "pil",
        callback: Optional[Callable[[int, torch.Tensor], None]] = None,
        callback_steps: int = 1,
    ) -> Union[torch.Tensor, List["Image.Image"]]:
        """Generate images from text prompts."""
        return self._get_generation_helper().generate(
            prompt,
            negative_prompt,
            height,
            width,
            num_inference_steps,
            guidance_scale,
            num_images_per_prompt,
            generator,
            latents,
            image,
            strength,
            output_type,
            callback,
            callback_steps,
        )
    
    def unload(self, components: Optional[List[str]] = None) -> None:
        """Unload components to free memory."""
        self._get_vae_helper().unload(components)
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.unload()
        except (RuntimeError, TypeError, AttributeError):
            # Ignore errors during interpreter shutdown
            pass
