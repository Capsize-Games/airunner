"""
Native Z-Image Pipeline Wrapper.

This module provides a wrapper around ZImageNativePipeline that exposes a 
diffusers-compatible interface for seamless integration with existing code.
"""


from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Union

import os
import torch
from PIL import Image

from airunner.components.art.managers.zimage.native.native_lora import (
    NativeLoraLoader,
    load_lora_state_dict,
)

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

    def load_lora_weights(
        self,
        pretrained_model_name_or_path_or_dict: Union[str, Dict[str, torch.Tensor]],
        weight_name: Optional[str] = None,
        adapter_name: Optional[str] = None,
        scale: float = 1.0,
        **kwargs,
    ) -> None:
        """Load LoRA into the native transformer.
        
        Uses native LoRA loader that works with FP8Linear layers.
        
        Args:
            pretrained_model_name_or_path_or_dict: Path to LoRA directory/file or state dict
            weight_name: Filename of the LoRA weights within the directory
            adapter_name: Name for the adapter
            scale: LoRA scale factor (0.0-1.0+)
            **kwargs: Additional arguments (for compatibility)
        """
        if self._native.transformer is None:
            raise ValueError("Transformer not loaded. Cannot apply LoRA.")
        
        # Handle the case where base path + weight_name is provided
        if weight_name is not None and isinstance(pretrained_model_name_or_path_or_dict, str):
            lora_path = os.path.join(pretrained_model_name_or_path_or_dict, weight_name)
        else:
            lora_path = pretrained_model_name_or_path_or_dict
        
        # Initialize loader if not exists
        if not hasattr(self, '_lora_loader') or self._lora_loader is None:
            self._lora_loader = NativeLoraLoader(self._native.transformer)
        
        # Load the LoRA
        success = self._lora_loader.load_lora(
            lora_path,
            scale=scale,
            adapter_name=adapter_name,
        )
        
        if not success:
            logger.warning(f"LoRA '{adapter_name}' loaded but no layers were modified")

    def unload_lora_weights(self, adapter_name: Optional[str] = None) -> None:
        """Unload LoRA weights from the pipeline.
        
        Args:
            adapter_name: Specific adapter to unload, or None to unload all
        """
        if not hasattr(self, '_lora_loader') or self._lora_loader is None:
            logger.debug("No LoRA loader initialized, nothing to unload")
            return
        
        if adapter_name is not None:
            self._lora_loader.remove_lora(adapter_name)
        else:
            self._lora_loader.remove_all_loras()
    
    def set_lora_enabled(self, adapter_name: str, enabled: bool) -> bool:
        """Enable or disable a specific LoRA adapter.
        
        Args:
            adapter_name: Name of the adapter
            enabled: Whether to enable or disable
            
        Returns:
            True if successful
        """
        if not hasattr(self, '_lora_loader') or self._lora_loader is None:
            logger.warning("No LoRA loader initialized")
            return False
        return self._lora_loader.set_lora_enabled(adapter_name, enabled)
    
    def set_all_loras_enabled(self, enabled: bool) -> None:
        """Enable or disable all LoRA adapters."""
        if not hasattr(self, '_lora_loader') or self._lora_loader is None:
            return
        self._lora_loader.set_all_loras_enabled(enabled)
    
    def set_lora_scale(self, adapter_name: str, scale: float) -> bool:
        """Set the scale for a LoRA adapter."""
        if not hasattr(self, '_lora_loader') or self._lora_loader is None:
            return False
        return self._lora_loader.set_lora_scale(adapter_name, scale)
    
    @property
    def loaded_loras(self) -> Dict[str, Any]:
        """Get info about loaded LoRAs."""
        if hasattr(self, '_lora_loader') and self._lora_loader is not None:
            return self._lora_loader.loaded_loras
        return {}
    
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
