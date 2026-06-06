"""Creation helpers for ChatModelFactory."""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel

from airunner_services.llm.adapters.chat_gguf_model_metadata import (
    UnsupportedGGUFArchitectureError,
)
from airunner_services.llm.adapters.chat_model_factory_helpers import (
    LocalRuntimeConfig,
    build_local_runtime_config,
    get_db_settings,
)
from airunner_services.llm.adapters.chat_model_factory_local_gguf_resolution import (
    has_valid_gguf_path,
    local_gguf_state,
    resolve_gguf_path,
    resolved_local_model_id,
    supports_local_gguf,
)
from airunner_services.llm.config.provider_config import LLMProviderConfig
from airunner_services.utils.model_optimizer import get_model_optimizer


def get_local_gguf_runtime_params(
    model_id: str | None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """Return llama.cpp runtime overrides for supported local GGUFs."""
    if not model_id:
        return {}

    runtime_params = LLMProviderConfig.get_gguf_runtime_profile(
        "local",
        model_id,
        profile_name=profile_name or "default",
    )
    return {
        key: value
        for key, value in runtime_params.items()
        if value is not None
    }


def _unsupported_gguf_architecture_message(
    error: UnsupportedGGUFArchitectureError,
) -> str:
    """Build a user-facing unsupported-architecture failure message."""
    version_message = ""
    if getattr(error, "runtime_version", None):
        version_message = f" Installed version: {error.runtime_version}."
    return (
        f"GGUF model architecture '{error.architecture}' is "
        "not yet supported by the installed llama-cpp-python runtime."
        f"{version_message} The model '{error.model_path}' requires a newer "
        "version of llama-cpp-python or a different GGUF build."
    )


def _create_gguf_chat_model(
    create_gguf_model: Callable[..., BaseChatModel],
    gguf_path: str,
    resolved_model_id: str | None,
    local_runtime: LocalRuntimeConfig,
    gguf_runtime_profile: str | None,
    gguf_params: dict[str, Any],
) -> BaseChatModel:
    """Create one configured GGUF chat model from resolved local inputs."""
    gguf_kwargs = _resolved_gguf_model_kwargs(
        resolved_model_id,
        local_runtime,
        gguf_runtime_profile,
        gguf_params,
    )
    try:
        return create_gguf_model(model_path=gguf_path, **gguf_kwargs)
    except UnsupportedGGUFArchitectureError as error:
        raise ValueError(
            _unsupported_gguf_architecture_message(error)
        ) from error


def create_local_model_from_settings(
    llm_settings: Any,
    chatbot: Any,
    model_path: str | None,
    gguf_runtime_profile: str | None,
    create_gguf_model: Callable[..., BaseChatModel],
) -> BaseChatModel | None:
    """Create one local GGUF chat model when the current settings allow it."""
    if not model_path:
        return None
    db_settings = get_db_settings()
    local_runtime = build_local_runtime_config(
        db_settings, llm_settings, chatbot
    )
    resolution = _resolved_local_gguf_path(
        db_settings,
        get_model_optimizer(),
        model_path,
        local_runtime.quantization_bits,
    )
    if resolution is None:
        return None
    return _local_chat_model(
        create_gguf_model, resolution, local_runtime, gguf_runtime_profile
    )


def _local_model_info(resolved_model_id: str | None) -> dict[str, Any]:
    """Return persisted model metadata for one resolved local model."""
    return LLMProviderConfig.get_model_info("local", resolved_model_id) or {}


def _gguf_chat_model_kwargs(
    model_info: dict[str, Any],
    local_runtime: LocalRuntimeConfig,
    gguf_runtime_profile: str | None,
    gguf_params: dict[str, Any],
) -> dict[str, Any]:
    """Build GGUF chat model kwargs from local runtime state."""
    return {
        "preferred_filename": model_info.get("gguf_filename"),
        "gguf_runtime_profile": gguf_runtime_profile,
        "enable_thinking": local_runtime.enable_thinking,
        "reasoning_effort": local_runtime.reasoning_effort,
        "tool_calling_mode": model_info.get("tool_calling_mode", "native"),
        **gguf_params,
    }


def _resolved_gguf_model_kwargs(
    resolved_model_id: str | None,
    local_runtime: LocalRuntimeConfig,
    gguf_runtime_profile: str | None,
    gguf_params: dict[str, Any],
) -> dict[str, Any]:
    """Return GGUF model kwargs after applying runtime profile overrides."""
    gguf_params.update(
        get_local_gguf_runtime_params(
            resolved_model_id,
            profile_name=gguf_runtime_profile,
        )
    )
    return _gguf_chat_model_kwargs(
        _local_model_info(resolved_model_id),
        local_runtime,
        gguf_runtime_profile,
        gguf_params,
    )


def _resolved_local_gguf_path(
    db_settings: Any,
    optimizer: Any,
    model_path: str,
    quantization_bits: int,
) -> tuple[str, str | None] | None:
    """Return the resolved GGUF path and final model ID when available."""
    resolved_model_id, allow_generic_scan, existing_gguf, generic_available = (
        local_gguf_state(db_settings, optimizer, model_path)
    )
    if not supports_local_gguf(
        quantization_bits, existing_gguf, generic_available
    ):
        return None
    gguf_path = _valid_gguf_path(
        optimizer,
        model_path,
        allow_generic_scan,
        existing_gguf,
        generic_available,
        quantization_bits,
    )
    if gguf_path is None:
        return None
    return gguf_path, resolved_local_model_id(resolved_model_id, gguf_path)


def _local_chat_model(
    create_gguf_model: Callable[..., BaseChatModel],
    resolution: tuple[str, str | None],
    local_runtime: LocalRuntimeConfig,
    gguf_runtime_profile: str | None,
) -> BaseChatModel:
    """Create one GGUF chat model from a resolved local path tuple."""
    gguf_path, resolved_model_id = resolution
    return _create_gguf_chat_model(
        create_gguf_model,
        gguf_path,
        resolved_model_id,
        local_runtime,
        gguf_runtime_profile,
        dict(local_runtime.gguf_params),
    )


def _valid_gguf_path(
    optimizer: Any,
    model_path: str,
    allow_generic_scan: bool,
    existing_gguf: str | None,
    generic_available: bool,
    quantization_bits: int,
) -> str | None:
    """Resolve and validate one GGUF path for local model loading."""
    gguf_path = resolve_gguf_path(
        optimizer,
        model_path,
        quantization_bits == 0,
        existing_gguf,
        generic_available,
        quantization_bits,
    )
    if not has_valid_gguf_path(optimizer, gguf_path, allow_generic_scan):
        return None
    return gguf_path
