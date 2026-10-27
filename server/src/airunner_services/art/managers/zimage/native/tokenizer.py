"""Tokenizer support for the native Z-Image text encoder."""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Union

import torch
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)


class ZImageTokenizer:
    """Z-Image tokenizer with chat-template formatting."""

    LLAMA_TEMPLATE = "<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"

    def __init__(
        self,
        tokenizer_path: Optional[str] = None,
        max_length: int = 512,
        padding: bool = True,
    ):
        self.max_length = max_length
        self.padding = padding
        self.pad_token_id = 151643
        self.tokenizer = None
        if tokenizer_path is not None:
            self._load_tokenizer(tokenizer_path)

    def _load_tokenizer(self, tokenizer_path: str):
        """Load the Qwen tokenizer."""
        try:
            if os.path.isdir(tokenizer_path):
                self.tokenizer = AutoTokenizer.from_pretrained(
                    tokenizer_path,
                    trust_remote_code=True,
                )
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    "Qwen/Qwen2.5-3B",
                    trust_remote_code=True,
                )
            logger.info("Loaded tokenizer from %s", tokenizer_path)
        except Exception as exc:
            logger.warning("Failed to load tokenizer: %s", exc)
            self.tokenizer = None

    def tokenize(
        self,
        text: Union[str, List[str]],
        llama_template: Optional[str] = None,
        return_tensors: str = "pt",
    ) -> Dict[str, torch.Tensor]:
        """Tokenize text with the Z-Image chat template."""
        if self.tokenizer is None:
            raise RuntimeError(
                "Tokenizer not loaded. Call _load_tokenizer first."
            )
        template = llama_template if llama_template else self.LLAMA_TEMPLATE
        texts = [text] if isinstance(text, str) else text
        formatted_texts = [template.format(item) for item in texts]
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
