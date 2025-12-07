"""
Native Z-Image Pipeline Wrapper.

This module provides a wrapper around ZImageNativePipeline that exposes a 
diffusers-compatible interface for seamless integration with existing code.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Union

import torch
from PIL import Image

logger = logging.getLogger(__name__)


class NativePipelineWrapper:
    """
    Wrapper around ZImageNativePipeline providing diffusers-compatible interface.
    
    This wrapper allows the native FP8 pipeline to be used with existing
    generation code that expects a diffusers-style pipeline interface.
    
    Key features:
    - Compatible __call__ interface
    - Exposes scheduler, transformer, text_encoder, vae, tokenizer attributes
    - Handles device management
    """
    
    def __init__(self, native_pipeline: Any):
        """
        Initialize wrapper.
        
        Args:
            native_pipeline: ZImageNativePipeline instance
        """
        self._native = native_pipeline
        self._device = native_pipeline.device
        
    @property
    def device(self) -> torch.device:
        """Get pipeline device."""
        return self._device
    
    @property
    def dtype(self) -> torch.dtype:
        """Get pipeline compute dtype."""
        return self._native.dtype
    
    @property
    def scheduler(self) -> Any:
        """Get scheduler."""
        return self._native.scheduler
    
    @scheduler.setter
    def scheduler(self, value: Any) -> None:
        """Set scheduler."""
        self._native.scheduler = value
    
    @property
    def transformer(self) -> Any:
        """Get transformer model."""
        return self._native.transformer
    
    @property
    def text_encoder(self) -> Any:
        """Get text encoder."""
        return self._native.text_encoder
    
    @property
    def tokenizer(self) -> Any:
        """Get tokenizer."""
        return self._native.tokenizer
    
    @property
    def vae(self) -> Any:
        """Get VAE."""
        return self._native.vae
    
    @property
    def is_native_fp8(self) -> bool:
        """Check if this is a native FP8 pipeline."""
        return True
    
    def to(self, device: Union[str, torch.device]) -> "NativePipelineWrapper":
        """Move pipeline to device.
        
        Args:
            device: Target device
            
        Returns:
            Self for chaining
        """
        if isinstance(device, str):
            device = torch.device(device)
        self._device = device
        # Native pipeline handles device movement internally
        return self
    
    def enable_model_cpu_offload(self, gpu_id: Optional[int] = None) -> None:
        """Enable CPU offload for memory efficiency.
        
        The native pipeline handles this differently - we set a flag
        that controls layer-by-layer loading during inference.
        """
        logger.info("Enabling CPU offload mode for native FP8 pipeline")
        if hasattr(self._native, 'enable_cpu_offload'):
            self._native.enable_cpu_offload(gpu_id)
    
    def enable_sequential_cpu_offload(self, gpu_id: Optional[int] = None) -> None:
        """Enable sequential CPU offload.
        
        Similar to enable_model_cpu_offload for native pipeline.
        """
        self.enable_model_cpu_offload(gpu_id)
    
    def __call__(
        self,
        prompt: Union[str, List[str]],
        prompt_2: Optional[Union[str, List[str]]] = None,
        negative_prompt: Optional[Union[str, List[str]]] = None,
        negative_prompt_2: Optional[Union[str, List[str]]] = None,
        height: int = 1024,
        width: int = 1024,
        num_inference_steps: int = 8,
        guidance_scale: float = 3.5,
        num_images_per_prompt: int = 1,
        generator: Optional[torch.Generator] = None,
        latents: Optional[torch.Tensor] = None,
        image: Optional[Any] = None,
        strength: float = 0.8,
        output_type: str = "pil",
        return_dict: bool = True,
        callback: Optional[Callable] = None,
        callback_steps: int = 1,
        **kwargs,
    ) -> Any:
        """
        Generate images from text prompt.
        
        This method provides a diffusers-compatible interface while using
        the native FP8 implementation under the hood.
        
        Args:
            prompt: Text prompt(s) for generation
            prompt_2: Secondary prompt (Z-Image uses single prompt)
            negative_prompt: Negative prompt(s)
            negative_prompt_2: Secondary negative prompt
            height: Image height in pixels
            width: Image width in pixels
            num_inference_steps: Number of denoising steps
            guidance_scale: Guidance scale (CFG)
            num_images_per_prompt: Number of images per prompt
            generator: Random generator for reproducibility
            latents: Optional initial latents
            output_type: Output format ("pil", "latent", "pt")
            return_dict: Whether to return dict or tuple
            callback: Progress callback function
            callback_steps: Steps between callbacks
            **kwargs: Additional arguments
            
        Returns:
            Generated images (format depends on output_type and return_dict)
        """
        # Diffusers-compatible callbacks: honor callback_on_step_end if provided
        callback_on_step_end = kwargs.pop("callback_on_step_end", None)
        step_callback = callback_on_step_end or callback
        step_callback_steps = kwargs.get("callback_steps", callback_steps)

        # Use the native pipeline's generate method
        images = self._native.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            height=height,
            width=width,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            num_images_per_prompt=num_images_per_prompt,
            generator=generator,
            latents=latents,
            image=image,
            strength=strength,
            output_type=output_type,
            callback=step_callback,
            callback_steps=step_callback_steps,
        )
        
        if return_dict:
            # Return diffusers-style output
            return PipelineOutput(images=images)
        
        return (images,)
    
    def unload(self) -> None:
        """Unload all models and free memory."""
        if hasattr(self._native, 'unload'):
            self._native.unload()


class PipelineOutput:
    """Simple output class mimicking diffusers pipeline output."""
    
    def __init__(self, images: List[Image.Image]):
        self.images = images
