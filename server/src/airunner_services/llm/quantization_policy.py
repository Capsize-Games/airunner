"""Shared quantization policy helpers for LLM runtime configuration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import torch
from transformers import BitsAndBytesConfig


def resolve_quantization_dtype(
    configured_dtype: Any,
    auto_select: Callable[[], str],
) -> tuple[str, bool]:
    """Return the effective dtype and whether it was auto-selected."""
    normalized = str(configured_dtype or "").strip().lower()
    if not normalized or normalized == "auto":
        return auto_select(), True
    return normalized, False


def create_bitsandbytes_config(
    dtype: str,
    *,
    four_bit_compute_dtype: Any = torch.bfloat16,
) -> BitsAndBytesConfig | None:
    """Return the BitsAndBytes config for one runtime dtype."""
    if dtype == "8bit":
        return BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
            llm_int8_enable_fp32_cpu_offload=True,
        )

    if dtype in {"4bit", "2bit"}:
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=four_bit_compute_dtype,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

    return None


def build_quantization_config_dict(
    dtype: str,
    *,
    four_bit_compute_dtype: str = "float16",
) -> dict[str, Any]:
    """Return the persisted BitsAndBytes payload for one config.json."""
    return {
        "load_in_4bit": dtype == "4bit",
        "load_in_8bit": dtype == "8bit",
        "llm_int8_threshold": 6.0,
        "llm_int8_has_fp16_weight": False,
        "bnb_4bit_compute_dtype": four_bit_compute_dtype,
        "bnb_4bit_use_double_quant": True,
        "bnb_4bit_quant_type": "nf4",
        "quant_method": "bitsandbytes",
    }