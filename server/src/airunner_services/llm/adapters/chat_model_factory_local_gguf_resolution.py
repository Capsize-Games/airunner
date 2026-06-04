"""Local GGUF discovery and path-resolution helpers for ChatModelFactory."""

from __future__ import annotations

import os
from typing import Any

from airunner_services.llm.adapters.chat_gguf import is_gguf_model
from airunner_services.llm.config.provider_config import LLMProviderConfig


def resolve_local_model_id(
    db_settings: Any,
    model_path: str | None,
) -> str | None:
    """Resolve one local model identifier from settings or model path."""
    if not model_path:
        model_id = getattr(db_settings, "model_id", None) if db_settings else None
        return model_id or None
    resolved_from_path = LLMProviderConfig.resolve_model_id(
        "local",
        os.path.basename(str(model_path)),
    )
    if resolved_from_path:
        return resolved_from_path
    model_id = getattr(db_settings, "model_id", None) if db_settings else None
    return model_id or None


def preferred_gguf_path(
    db_settings: Any,
    model_path: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return preferred persisted GGUF metadata and file path."""
    if db_settings is None:
        return None, None
    model_id = getattr(db_settings, "model_id", None)
    if not model_id:
        return None, None
    gguf_info = LLMProviderConfig.get_gguf_info("local", model_id)
    if not gguf_info or str(model_path).endswith(".gguf"):
        return gguf_info, None
    candidate = os.path.join(model_path, gguf_info["filename"])
    return gguf_info, candidate if os.path.exists(candidate) else None


def allow_generic_directory_scan(
    model_path: str,
    gguf_info: dict[str, Any] | None,
) -> bool:
    """Return whether generic GGUF discovery should scan the directory."""
    return gguf_info is None or str(model_path).endswith(".gguf")


def existing_gguf_path(
    optimizer: Any,
    model_path: str,
    preferred_path: str | None,
    allow_generic_scan: bool,
) -> str | None:
    """Return an already existing GGUF path when one is available."""
    if preferred_path:
        return preferred_path
    if not allow_generic_scan:
        return None
    return optimizer.find_existing_gguf(model_path)


def generic_gguf_available(
    model_path: str,
    allow_generic_scan: bool,
) -> bool:
    """Return whether the provided path already points to GGUF content."""
    return is_gguf_model(model_path) if allow_generic_scan else False


def resolve_gguf_path(
    optimizer: Any,
    model_path: str,
    use_gguf: bool,
    existing_gguf: str | None,
    generic_gguf_available_value: bool,
    quantization_bits: int,
) -> str | None:
    """Resolve the GGUF path, converting when required and possible."""
    gguf_path = existing_gguf or model_path
    if use_gguf and not existing_gguf and not generic_gguf_available_value:
        quant_type = optimizer.bits_to_gguf_quantization(quantization_bits)
        converted = optimizer.ensure_gguf(model_path, quant_type)
        if converted:
            gguf_path = converted
    return gguf_path


def has_valid_gguf_path(
    optimizer: Any,
    gguf_path: str | None,
    allow_generic_scan: bool,
) -> bool:
    """Return whether the resolved path can be loaded as GGUF."""
    if not gguf_path:
        return False
    if str(gguf_path).endswith(".gguf"):
        return True
    if not allow_generic_scan:
        return False
    return bool(
        is_gguf_model(gguf_path) or optimizer.find_existing_gguf(gguf_path)
    )


def local_gguf_state(
    db_settings: Any,
    optimizer: Any,
    model_path: str,
) -> tuple[str | None, bool, str | None, bool]:
    """Return resolved GGUF discovery state for one local model path."""
    resolved_model_id = resolve_local_model_id(db_settings, model_path)
    gguf_info, preferred_path = preferred_gguf_path(db_settings, model_path)
    allow_generic_scan = allow_generic_directory_scan(model_path, gguf_info)
    existing_path = existing_gguf_path(
        optimizer,
        model_path,
        preferred_path,
        allow_generic_scan,
    )
    generic_available = generic_gguf_available(model_path, allow_generic_scan)
    return resolved_model_id, allow_generic_scan, existing_path, generic_available


def supports_local_gguf(
    quantization_bits: int,
    existing_gguf: str | None,
    generic_available: bool,
) -> bool:
    """Return whether local settings can proceed with a GGUF runtime."""
    return bool(quantization_bits == 0 or existing_gguf or generic_available)


def resolved_local_model_id(
    resolved_model_id: str | None,
    gguf_path: str | None,
) -> str | None:
    """Return the final local model identifier after GGUF resolution."""
    if resolved_model_id is not None:
        return resolved_model_id
    return resolve_local_model_id(None, gguf_path)