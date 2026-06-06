"""Model-state helpers for HuggingFace generation mixins."""

from __future__ import annotations

from typing import Any, Optional

import torch


def get_token_ids(adapter: Any) -> tuple[int, int]:
    """Return EOS and PAD token IDs for one adapter."""
    if adapter.use_mistral_native and adapter._mistral_tokenizer:
        eos_token_id = (
            adapter._mistral_tokenizer.instruct_tokenizer.tokenizer.eos_id
        )
        return eos_token_id, eos_token_id
    if adapter.tokenizer:
        eos_token_id = adapter.tokenizer.eos_token_id
        return eos_token_id, eos_token_id
    return 2, 2


def is_quantized_model(adapter: Any) -> bool:
    """Return whether the current model uses 4-bit or 8-bit quantization."""
    try:
        if hasattr(adapter.model, "config"):
            config = adapter.model.config
            if hasattr(config, "quantization_config"):
                return True
        if (
            hasattr(adapter.model, "is_loaded_in_4bit")
            and adapter.model.is_loaded_in_4bit
        ):
            return True
        if (
            hasattr(adapter.model, "is_loaded_in_8bit")
            and adapter.model.is_loaded_in_8bit
        ):
            return True
    except Exception:
        return False
    return False


def get_model_dtype(adapter: Any) -> Optional[torch.dtype]:
    """Return the model floating dtype when it can be determined."""
    try:
        if hasattr(adapter.model, "dtype"):
            return adapter.model.dtype
        param = next(adapter.model.parameters(), None)
        if param is not None:
            return param.dtype
    except Exception:
        return None
    return None


def run_generation(
    adapter: Any,
    inputs: dict[str, Any],
    eos_token_id: int,
    pad_token_id: int,
    kwargs: dict[str, Any],
) -> Any:
    """Run one non-streaming model generation call."""
    with torch.no_grad():
        return adapter.model.generate(
            **_generation_kwargs(
                adapter,
                inputs,
                eos_token_id,
                pad_token_id,
                kwargs,
            )
        )


def _generation_kwargs(
    adapter: Any,
    inputs: dict[str, Any],
    eos_token_id: int,
    pad_token_id: int,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Build one non-streaming generation kwargs dictionary."""
    return {
        **inputs,
        **_sampling_kwargs(adapter, kwargs),
        "pad_token_id": pad_token_id,
        "eos_token_id": eos_token_id,
        "use_cache": True,
    }


def _sampling_kwargs(adapter: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Build shared sampling kwargs for non-streaming generation."""
    return {
        "max_new_tokens": kwargs.get("max_new_tokens", adapter.max_new_tokens),
        "temperature": kwargs.get("temperature", adapter.temperature),
        "top_p": kwargs.get("top_p", adapter.top_p),
        "top_k": kwargs.get("top_k", adapter.top_k),
        "repetition_penalty": kwargs.get(
            "repetition_penalty",
            adapter.repetition_penalty,
        ),
        "do_sample": kwargs.get("do_sample", adapter.do_sample),
    }
