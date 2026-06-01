"""Prompt-conditioning helpers for the native Z-Image pipeline."""

from __future__ import annotations

import gc
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import torch

from airunner_services.art.managers.zimage.native.zimage_text_encoder import (
    ZImageTextEncoder,
)

logger = logging.getLogger(__name__)


class ZImageNativePipelinePromptHelper:
    """Manage text-encoder loading and prompt-conditioning state."""

    def __init__(self, owner) -> None:
        """Store the owning native pipeline."""
        self._owner = owner

    def load_text_encoder(
        self,
        model_path: Optional[str] = None,
        tokenizer_path: Optional[str] = None,
        use_4bit: bool = False,
    ) -> None:
        """Load the text encoder and tokenizer."""
        path = model_path or self._owner.text_encoder_path
        if path is None:
            raise ValueError("No text encoder path provided")
        tok_path = tokenizer_path
        if tok_path is None:
            sibling_tokenizer = os.path.join(os.path.dirname(path), "tokenizer")
            tok_path = sibling_tokenizer if os.path.isdir(sibling_tokenizer) else path
        logger.info("Loading text encoder from %s", path)
        quantization = (
            "4bit" if use_4bit else self._owner.text_encoder_quantization
        )
        plan = self.build_text_encoder_load_plan(quantization)
        self._owner.text_encoder = ZImageTextEncoder(
            model_path=path,
            tokenizer_path=tok_path,
            device=plan["device"],
            dtype=self._owner.dtype,
            quantization=plan["quantization"],
            device_map=plan["device_map"],
            max_memory=plan["max_memory"],
            enable_cpu_offload=plan["enable_cpu_offload"],
        )
        self._owner.tokenizer = self._owner.text_encoder.tokenizer
        self._owner._loaded_components.append("text_encoder")
        logger.info("Text encoder loaded successfully")

    def build_text_encoder_load_plan(
        self,
        quantization: Optional[str],
    ) -> Dict[str, Any]:
        """Choose a text-encoder loading strategy for current free VRAM."""
        plan = {
            "quantization": quantization,
            "device": self._owner.device,
            "device_map": None,
            "max_memory": None,
            "enable_cpu_offload": False,
        }
        if not torch.cuda.is_available():
            return plan
        free_vram_gb = torch.cuda.mem_get_info()[0] / (1024**3)
        total_vram_gb = (
            torch.cuda.get_device_properties(0).total_memory / (1024**3)
        )
        cpu_budget = "32GiB"
        if quantization in {"4bit", "8bit"} and free_vram_gb < 4.0:
            logger.info(
                "Low free VRAM after transformer load (%.2f GiB). "
                "Loading text encoder on CPU to avoid prompt-encoding OOMs.",
                free_vram_gb,
            )
            plan.update(
                {
                    "quantization": None,
                    "device": torch.device("cpu"),
                    "device_map": None,
                    "max_memory": None,
                    "enable_cpu_offload": False,
                }
            )
            return plan
        gpu_budget = max(
            int(max(min(total_vram_gb - 8.0, free_vram_gb - 1.0), 2.0)),
            2,
        )
        logger.info(
            "Text encoder load budget: free_vram=%.2f GiB, total_vram=%.2f GiB, gpu_budget=%sGiB.",
            free_vram_gb,
            total_vram_gb,
            gpu_budget,
        )
        plan.update(
            {
                "device_map": "auto",
                "max_memory": {0: f"{gpu_budget}GiB", "cpu": cpu_budget},
            }
        )
        return plan

    def ensure_text_encoder_ready(self) -> None:
        """Load text encoder weights on demand before prompt encoding."""
        text_encoder = self._owner.text_encoder
        if text_encoder is None:
            raise RuntimeError("Text encoder not loaded")
        if text_encoder.model is None and text_encoder.model_path:
            logger.info("Reloading text encoder for prompt encoding")
            text_encoder.load_model(text_encoder.model_path)

    def prepare_text_encoder_for_encoding(self) -> None:
        """Move fully GPU-resident encoders back to the active device."""
        self.ensure_text_encoder_ready()
        text_encoder = self._owner.text_encoder
        if text_encoder is None or text_encoder.model is None:
            return
        if text_encoder.prefer_cpu_execution:
            logger.debug("Keeping text encoder on CPU for prompt encoding")
            return
        if text_encoder.uses_accelerate_offload:
            logger.debug("Using accelerate-managed text encoder placement")
            return
        current_device = next(text_encoder.model.parameters()).device
        if current_device.type == "cpu":
            logger.debug("Moving text encoder back to GPU for encoding")
            text_encoder.model.to(self._owner.device)

    def release_text_encoder_after_encoding(self) -> None:
        """Free text-encoder GPU memory once prompt embeddings are ready."""
        text_encoder = self._owner.text_encoder
        if text_encoder is None or text_encoder.model is None:
            return
        if text_encoder.prefer_cpu_execution:
            logger.debug("Keeping CPU-resident text encoder loaded")
            return
        if text_encoder.uses_accelerate_offload:
            text_encoder.unload_model()
            logger.debug("Released accelerate-managed text encoder after encoding")
            return
        text_encoder.model.to("cpu")
        gc.collect()
        torch.cuda.empty_cache()
        logger.debug("Offloaded text encoder to CPU")

    def move_prompt_conditioning_to_device(
        self,
        prompt_embeds: torch.Tensor,
        negative_embeds: Optional[torch.Tensor],
        attention_mask: Optional[torch.Tensor],
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """Move prompt-conditioning tensors to the transformer device."""
        prompt_embeds = prompt_embeds.to(
            device=self._owner.device,
            dtype=self._owner.dtype,
        )
        if negative_embeds is not None:
            negative_embeds = negative_embeds.to(
                device=self._owner.device,
                dtype=self._owner.dtype,
            )
        if attention_mask is not None:
            attention_mask = attention_mask.to(self._owner.device)
        return prompt_embeds, negative_embeds, attention_mask

    def encode_prompt(
        self,
        prompt: Union[str, List[str]],
        negative_prompt: Optional[Union[str, List[str]]] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """Encode one positive and optional negative prompt pair."""
        text_encoder = self._owner.text_encoder
        if text_encoder is None:
            raise RuntimeError("Text encoder not loaded")
        prompt_embeds, attention_mask = text_encoder.encode(
            prompt,
            return_attention_mask=True,
        )
        negative_embeds = None
        if negative_prompt is not None:
            negative_embeds, _ = text_encoder.encode(
                negative_prompt,
                return_attention_mask=False,
            )
        return prompt_embeds, negative_embeds, attention_mask