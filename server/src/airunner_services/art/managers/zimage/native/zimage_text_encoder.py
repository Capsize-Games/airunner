"""
Z-Image Text Encoder and Tokenizer.

This module provides the Qwen-based text encoder and tokenizer
for Z-Image, using the chat template format.

Based on ComfyUI's comfy/text_encoders/z_image.py implementation.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn

from airunner_services.art.managers.zimage.native.zimage_text_encoder_loader_helper import (
    ZImageTextEncoderLoaderHelper,
)
from airunner_services.art.runtime_memory import clear_memory
from airunner_services.art.managers.zimage.native.zimage_tokenizer import (
    ZImageTokenizer,
)

logger = logging.getLogger(__name__)


class ZImageTextEncoder(nn.Module):
    """
    Z-Image text encoder wrapper.

    Wraps a Qwen model for text encoding, supporting quantization
    for memory efficiency.

    Args:
        model_path: Path to text encoder model
        tokenizer_path: Path to tokenizer (defaults to model_path)
        device: Target device
        dtype: Data type
        quantization: Quantization level (None, "4bit", "8bit")
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        tokenizer_path: Optional[str] = None,
        device: Optional[torch.device] = None,
        dtype: Optional[torch.dtype] = None,
        quantization: Optional[str] = None,
        device_map: Optional[str] = None,
        max_memory: Optional[Dict[str, str]] = None,
        enable_cpu_offload: bool = False,
    ):
        super().__init__()

        self.model_path = model_path
        self.tokenizer_path = tokenizer_path
        self.dtype = dtype or torch.bfloat16
        self.quantization = quantization
        self._device = device
        self._device_map = device_map
        self._max_memory = max_memory
        self._enable_cpu_offload = enable_cpu_offload
        self._prefer_cpu_execution = (
            device is not None and torch.device(device).type == "cpu"
        )

        self.model: Optional[nn.Module] = None
        self.tokenizer: Optional[ZImageTokenizer] = None

        # Hidden state extraction settings
        self.layer_idx = -2  # Second to last layer

        if model_path is not None:
            self.load_model(model_path)

    def _get_loader_helper(self) -> ZImageTextEncoderLoaderHelper:
        """Return the cached text-encoder loader helper."""
        helper = getattr(self, "_loader_helper", None)
        if helper is None:
            helper = ZImageTextEncoderLoaderHelper(self)
            self._loader_helper = helper
        return helper

    @property
    def device(self) -> torch.device:
        """Get model device."""
        if self.model is not None:
            return next(self.model.parameters()).device
        return self._device or torch.device("cpu")

    @property
    def hidden_size(self) -> int:
        """Get hidden size of text encoder."""
        return 2560  # Qwen3-4B hidden size

    def load_model(self, model_path: str):
        """Load the text encoder model."""
        self._get_loader_helper().load_model(model_path)

    @property
    def uses_accelerate_offload(self) -> bool:
        """Return True when the loaded model uses a mixed device map."""
        if self.model is None:
            return False
        device_map = getattr(self.model, "hf_device_map", None)
        if not isinstance(device_map, dict):
            return False
        return any(target in {"cpu", "disk"} for target in device_map.values())

    @property
    def prefer_cpu_execution(self) -> bool:
        """Return True when prompt encoding should stay on CPU."""
        return self._prefer_cpu_execution

    def unload_model(self) -> None:
        """Release model weights while keeping tokenizer and load settings."""
        if self.model is None:
            return
        device = getattr(self.model, "device", None)
        del self.model
        self.model = None
        clear_memory(device)

    def encode(
        self,
        text: Union[str, List[str]],
        return_attention_mask: bool = True,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Encode text to embeddings.

        Args:
            text: Input text or list of texts
            return_attention_mask: Whether to return attention mask

        Returns:
            Tuple of (embeddings, attention_mask)
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded. Call load_model first.")

        # Tokenize
        tokens = self.tokenizer.tokenize(text)
        input_ids = tokens["input_ids"].to(self.device)
        attention_mask = tokens["attention_mask"].to(self.device)

        # Forward pass
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
            )

        # Get hidden state from specified layer
        hidden_states = outputs.hidden_states[self.layer_idx]

        if return_attention_mask:
            return hidden_states, attention_mask
        return hidden_states, None

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass with pre-tokenized input.

        Args:
            input_ids: Token IDs of shape (B, L)
            attention_mask: Optional attention mask

        Returns:
            Hidden states of shape (B, L, D)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded.")

        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
            )

        return outputs.hidden_states[self.layer_idx]

    def unload(self):
        """Unload model to free memory."""
        device = getattr(self.model, "device", None)
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        clear_memory(device)


class SimpleTextEncoder(nn.Module):
    """
    Simple text encoder for testing without full Qwen model.

    Uses random projections for text encoding - NOT for production use.

    Args:
        vocab_size: Vocabulary size
        hidden_size: Output hidden size
        max_length: Maximum sequence length
    """

    def __init__(
        self,
        vocab_size: int = 151936,
        hidden_size: int = 2560,
        max_length: int = 512,
    ):
        super().__init__()

        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.max_length = max_length

        # Simple embedding + projection
        self.embedding = nn.Embedding(vocab_size, hidden_size)
        self.proj = nn.Linear(hidden_size, hidden_size)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            input_ids: Token IDs
            attention_mask: Optional mask (unused)

        Returns:
            Embeddings
        """
        x = self.embedding(input_ids)
        x = self.proj(x)
        return x
