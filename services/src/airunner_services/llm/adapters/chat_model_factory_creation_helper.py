"""Creation helpers for ChatModelFactory."""

from __future__ import annotations

import os
from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel

from airunner_services.llm.adapters.chat_gguf import (
    UnsupportedGGUFArchitectureError,
    is_gguf_model,
)
from airunner_services.llm.adapters.chat_model_factory_helpers import (
    LocalRuntimeConfig,
    ProviderRuntimeConfig,
    build_local_runtime_config,
    get_db_settings,
)
from airunner_services.llm.config.provider_config import LLMProviderConfig
from airunner_services.utils.model_optimizer import get_model_optimizer


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
    return {key: value for key, value in runtime_params.items() if value is not None}


def _preferred_gguf_path(
    db_settings: Any,
    model_path: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return the preferred persisted GGUF metadata and file path."""
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


def _allow_generic_directory_scan(
    model_path: str,
    gguf_info: dict[str, Any] | None,
) -> bool:
    """Return whether generic GGUF discovery should scan the directory."""
    return gguf_info is None or str(model_path).endswith(".gguf")


def _existing_gguf_path(
    optimizer: Any,
    model_path: str,
    preferred_gguf_path: str | None,
    allow_generic_directory_scan: bool,
) -> str | None:
    """Return an already existing GGUF path when one is available."""
    if preferred_gguf_path:
        return preferred_gguf_path
    if not allow_generic_directory_scan:
        return None
    return optimizer.find_existing_gguf(model_path)


def _generic_gguf_available(
    model_path: str,
    allow_generic_directory_scan: bool,
) -> bool:
    """Return whether the provided path already points to GGUF content."""
    return is_gguf_model(model_path) if allow_generic_directory_scan else False


def _resolve_gguf_path(
    optimizer: Any,
    model_path: str,
    use_gguf: bool,
    existing_gguf: str | None,
    generic_gguf_available: bool,
    quantization_bits: int,
) -> str | None:
    """Resolve the GGUF path, converting when required and possible."""
    gguf_path = existing_gguf or model_path
    if use_gguf and not existing_gguf and not generic_gguf_available:
        quant_type = optimizer.bits_to_gguf_quantization(quantization_bits)
        converted = optimizer.ensure_gguf(model_path, quant_type)
        if converted:
            gguf_path = converted
    return gguf_path


def _has_valid_gguf_path(
    optimizer: Any,
    gguf_path: str | None,
    allow_generic_directory_scan: bool,
) -> bool:
    """Return whether the resolved path can be loaded as GGUF."""
    if not gguf_path:
        return False
    if str(gguf_path).endswith(".gguf"):
        return True
    if not allow_generic_directory_scan:
        return False
    return bool(
        is_gguf_model(gguf_path) or optimizer.find_existing_gguf(gguf_path)
    )


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
    gguf_params.update(
        get_local_gguf_runtime_params(
            resolved_model_id,
            profile_name=gguf_runtime_profile,
        )
    )
    model_info = LLMProviderConfig.get_model_info("local", resolved_model_id) or {}
    try:
        return create_gguf_model(
            model_path=gguf_path,
            preferred_filename=model_info.get("gguf_filename"),
            gguf_runtime_profile=gguf_runtime_profile,
            enable_thinking=local_runtime.enable_thinking,
            reasoning_effort=local_runtime.reasoning_effort,
            tool_calling_mode=model_info.get("tool_calling_mode", "native"),
            **gguf_params,
        )
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
    local_runtime = build_local_runtime_config(db_settings, llm_settings, chatbot)
    optimizer = get_model_optimizer()
    resolved_model_id = resolve_local_model_id(db_settings, model_path)
    use_gguf = local_runtime.quantization_bits == 0
    gguf_info, preferred_gguf_path = _preferred_gguf_path(db_settings, model_path)
    allow_generic_scan = _allow_generic_directory_scan(model_path, gguf_info)
    existing_gguf = _existing_gguf_path(
        optimizer,
        model_path,
        preferred_gguf_path,
        allow_generic_scan,
    )
    generic_gguf_available = _generic_gguf_available(
        model_path,
        allow_generic_scan,
    )
    if not (use_gguf or existing_gguf or generic_gguf_available):
        return None

    gguf_path = _resolve_gguf_path(
        optimizer,
        model_path,
        use_gguf,
        existing_gguf,
        generic_gguf_available,
        local_runtime.quantization_bits,
    )
    if not _has_valid_gguf_path(optimizer, gguf_path, allow_generic_scan):
        return None

    resolved_model_id = resolved_model_id or resolve_local_model_id(None, gguf_path)
    return _create_gguf_chat_model(
        create_gguf_model,
        gguf_path,
        resolved_model_id,
        local_runtime,
        gguf_runtime_profile,
        dict(local_runtime.gguf_params),
    )


def create_provider_model_from_runtime(
    provider_runtime: ProviderRuntimeConfig,
    create_openrouter_model: Callable[..., BaseChatModel],
    create_ollama_model: Callable[..., BaseChatModel],
    create_openai_model: Callable[..., BaseChatModel],
) -> BaseChatModel | None:
    """Create one non-local chat model from the resolved provider runtime."""
    if provider_runtime.provider == "openrouter":
        if not provider_runtime.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable required for OpenRouter"
            )
        return create_openrouter_model(
            api_key=provider_runtime.api_key,
            model_name=provider_runtime.model_name or "mistralai/mistral-7b-instruct",
            temperature=provider_runtime.temperature,
            max_tokens=provider_runtime.max_tokens,
        )

    if provider_runtime.provider == "ollama":
        return create_ollama_model(
            model_name=provider_runtime.model_name or "llama2",
            base_url=provider_runtime.base_url or "http://localhost:11434",
            temperature=provider_runtime.temperature,
        )

    if provider_runtime.provider != "openai":
        return None
    if not provider_runtime.api_key:
        raise ValueError("OPENAI_API_KEY environment variable required for OpenAI")
    return create_openai_model(
        api_key=provider_runtime.api_key,
        model_name=provider_runtime.model_name or "gpt-4",
        temperature=provider_runtime.temperature,
        max_tokens=provider_runtime.max_tokens,
    )