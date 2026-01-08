"""
Z-Image Text Encoder and Tokenizer.

This module provides the Qwen-based text encoder and tokenizer
for Z-Image, using the chat template format.

Based on ComfyUI's comfy/text_encoders/z_image.py implementation.
"""

from __future__ import annotations

import logging
import os
import gc
from typing import Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from transformers import (
    Qwen2Tokenizer,
    AutoTokenizer,
    AutoModel,
    AutoConfig,
    BitsAndBytesConfig,
)

logger = logging.getLogger(__name__)


class ZImageTokenizer:
    """
    Z-Image tokenizer with chat template formatting.
    
    Uses Qwen2.5 tokenizer with special chat template for Z-Image.
    
    Args:
        tokenizer_path: Path to tokenizer files
        max_length: Maximum sequence length
        padding: Whether to pad sequences
    """
    
    LLAMA_TEMPLATE = "<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"
    
    def __init__(
        self,
        tokenizer_path: Optional[str] = None,
        max_length: int = 512,
        padding: bool = True,
    ):
        self.max_length = max_length
        self.padding = padding
        self.pad_token_id = 151643  # Qwen pad token
        
        # Try to load tokenizer
        self.tokenizer = None
        if tokenizer_path is not None:
            self._load_tokenizer(tokenizer_path)
    
    def _load_tokenizer(self, tokenizer_path: str):
        """Load the Qwen tokenizer."""
        # Use module-level transformers imports
        try:
            if os.path.isdir(tokenizer_path):
                self.tokenizer = AutoTokenizer.from_pretrained(
                    tokenizer_path,
                    trust_remote_code=True,
                )
            else:
                # Try loading from model name
                self.tokenizer = AutoTokenizer.from_pretrained(
                    "Qwen/Qwen2.5-3B",  # Fallback
                    trust_remote_code=True,
                )
            logger.info(f"Loaded tokenizer from {tokenizer_path}")
        except Exception as e:
            logger.warning(f"Failed to load tokenizer: {e}")
            self.tokenizer = None
    
    def tokenize(
        self,
        text: Union[str, List[str]],
        llama_template: Optional[str] = None,
        return_tensors: str = "pt",
    ) -> Dict[str, torch.Tensor]:
        """
        Tokenize text with chat template.
        
        Args:
            text: Input text or list of texts
            llama_template: Optional custom template
            return_tensors: Return type ("pt" for PyTorch)
            
        Returns:
            Dictionary with input_ids and attention_mask
        """
        if self.tokenizer is None:
            raise RuntimeError("Tokenizer not loaded. Call _load_tokenizer first.")
        
        template = llama_template if llama_template else self.LLAMA_TEMPLATE
        
        if isinstance(text, str):
            texts = [text]
        else:
            texts = text
        
        # Apply template
        formatted_texts = [template.format(t) for t in texts]
        
        # Tokenize
        encoding = self.tokenizer(
            formatted_texts,
            padding=self.padding,
            truncation=True,
            max_length=self.max_length,
            return_tensors=return_tensors,
        )
        
        return {
            "input_ids": encoding["input_ids"],
            "attention_mask": encoding["attention_mask"],
        }
    
    def decode(self, token_ids: torch.Tensor) -> str:
        """Decode token IDs back to text."""
        if self.tokenizer is None:
            raise RuntimeError("Tokenizer not loaded.")
        return self.tokenizer.decode(token_ids, skip_special_tokens=True)


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
    ):
        super().__init__()
        
        self.model_path = model_path
        self.tokenizer_path = tokenizer_path
        self.dtype = dtype or torch.bfloat16
        self.quantization = quantization
        self._device = device
        self._device_map = device_map
        self._max_memory = max_memory
        
        self.model: Optional[nn.Module] = None
        self.tokenizer: Optional[ZImageTokenizer] = None
        
        # Hidden state extraction settings
        self.layer_idx = -2  # Second to last layer
        
        if model_path is not None:
            self.load_model(model_path)
    
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
        """
        Load the text encoder model.
        
        Args:
            model_path: Path to model weights
        """
        try:
            # Model imports are handled at module level
            
            # Load config
            config = AutoConfig.from_pretrained(
                model_path,
                trust_remote_code=True,
            )
            
            # Configure quantization
            quantization_config = None
            if self.quantization == "4bit":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=self.dtype,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
            elif self.quantization == "8bit":
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                )
            
            # Load model
            # Choose device_map strategy: prefer provided map, else auto when quantized
            device_map = self._device_map
            if device_map is None and (quantization_config is not None or self._device is None):
                device_map = "auto"

            load_kwargs = {
                "config": config,
                "quantization_config": quantization_config,
                "torch_dtype": self.dtype,
                "device_map": device_map,
                "trust_remote_code": True,
            }
            if device_map is not None and self._max_memory is not None:
                load_kwargs["max_memory"] = self._max_memory

            self.model = AutoModel.from_pretrained(
                model_path,
                **load_kwargs,
            )
            
            if self._device is not None and quantization_config is None:
                self.model = self.model.to(self._device)
            
            self.model.eval()
            
            # Load tokenizer from tokenizer_path if provided, else from model_path
            tok_path = self.tokenizer_path if self.tokenizer_path else model_path
            self.tokenizer = ZImageTokenizer(tok_path)
            
            logger.info(f"Loaded text encoder from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load text encoder: {e}")
            raise
    
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
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        gc.collect()
        torch.cuda.empty_cache()


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
