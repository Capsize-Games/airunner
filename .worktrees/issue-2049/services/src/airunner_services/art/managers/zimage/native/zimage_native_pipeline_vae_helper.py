"""VAE and scheduler helpers for the native Z-Image pipeline."""

from __future__ import annotations

import logging
from typing import List, Optional, Union

import numpy as np
from PIL import Image
import torch

from airunner_services.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)
from airunner_services.art.runtime_memory import clear_memory
from diffusers import AutoencoderKL

logger = logging.getLogger(__name__)


class NativeVaeImageProcessor:
    """Lightweight VAE image processor to avoid diffusers dependency."""

    def __init__(self, vae_scale_factor: int = 8):
        self.vae_scale_factor = vae_scale_factor

    def _ensure_multiple(self, value: int) -> int:
        if self.vae_scale_factor <= 0:
            return value
        return int(value // self.vae_scale_factor * self.vae_scale_factor)

    def preprocess(
        self,
        image: Union[Image.Image, List[Image.Image], torch.Tensor],
        height: int,
        width: int,
    ) -> torch.Tensor:
        """Resize and normalize one image batch to [-1, 1]."""
        if isinstance(image, torch.Tensor):
            return image
        images = image if isinstance(image, list) else [image]
        target_h = self._ensure_multiple(height)
        target_w = self._ensure_multiple(width)
        tensors = []
        for img in images:
            if not isinstance(img, Image.Image):
                raise ValueError("Expected PIL Image for preprocess")
            img = img.convert("RGB")
            img = img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)
            arr = np.array(img).astype(np.float32) / 255.0
            arr = torch.from_numpy(arr).permute(2, 0, 1)
            tensors.append(arr * 2.0 - 1.0)
        return torch.stack(tensors, dim=0)


class ZImageNativePipelineVaeHelper:
    """Manage VAE loading, scheduler setup, and cleanup."""

    def __init__(self, owner) -> None:
        """Store the owning native pipeline."""
        self._owner = owner

    def ensure_image_processor(self) -> None:
        """Create the lightweight VAE image processor on first use."""
        if self._owner.image_processor is not None:
            return
        try:
            vae_scale_factor = 2 ** (len(self._owner.vae.config.block_out_channels) - 1)
        except Exception:
            vae_scale_factor = 8
        self._owner.image_processor = NativeVaeImageProcessor(vae_scale_factor)

    def ensure_vae_on_device(self) -> None:
        """Move the VAE to the active device before encode/decode."""
        if self._owner.vae is None:
            raise RuntimeError("VAE not loaded")
        vae_device = next(self._owner.vae.parameters()).device
        if vae_device != self._owner.device:
            logger.debug("Moving VAE from %s to %s", vae_device, self._owner.device)
            self._owner.vae.to(self._owner.device)

    def load_vae(self, vae_path: Optional[str] = None) -> None:
        """Load the VAE decoder."""
        path = vae_path or self._owner.vae_path
        if path is None:
            raise ValueError("No VAE path provided")
        logger.info("Loading VAE from %s", path)
        vae_device = self._owner.device
        if self._owner.device.type == "cuda":
            vae_device = torch.device("cpu")
            logger.info("Loading VAE on CPU; it will move to GPU on first use")
        self._owner.vae = AutoencoderKL.from_pretrained(
            path,
            torch_dtype=self._owner.dtype,
        ).to(vae_device)
        self._owner.vae.eval()
        if hasattr(self._owner.vae, "enable_slicing"):
            self._owner.vae.enable_slicing()
        if hasattr(self._owner.vae, "enable_tiling"):
            self._owner.vae.enable_tiling()
        self.ensure_image_processor()
        self._owner._loaded_components.append("vae")
        logger.info("VAE loaded successfully")

    def setup_scheduler(
        self,
        num_inference_steps: int = 4,
        shift: float = 3.0,
    ) -> None:
        """Set up the flow matching scheduler."""
        del shift
        self._owner.scheduler = FlowMatchEulerScheduler()
        self._owner.scheduler.set_timesteps(
            num_inference_steps,
            device=self._owner.device,
        )
        logger.info(
            "Scheduler setup with %s steps (FlowMatchEulerScheduler)",
            num_inference_steps,
        )

    def unload(self, components: Optional[List[str]] = None) -> None:
        """Unload selected components and free memory."""
        components = components or ["transformer", "text_encoder", "vae"]
        if "transformer" in components and self._owner.transformer is not None:
            del self._owner.transformer
            self._owner.transformer = None
            self._remove_loaded_component("transformer")
        if "text_encoder" in components and self._owner.text_encoder is not None:
            self._owner.text_encoder.unload()
            self._owner.text_encoder = None
            self._owner.tokenizer = None
            self._remove_loaded_component("text_encoder")
        if "vae" in components and self._owner.vae is not None:
            del self._owner.vae
            self._owner.vae = None
            self._remove_loaded_component("vae")
        clear_memory(self._owner.device)
        logger.info("Unloaded components: %s", components)

    def _remove_loaded_component(self, name: str) -> None:
        """Remove one component name from the loaded-component registry."""
        if name in self._owner._loaded_components:
            self._owner._loaded_components.remove(name)