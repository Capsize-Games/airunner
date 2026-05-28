"""Helper functions for ChatModelFactory settings resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LocalRuntimeConfig:
    """Resolved persisted runtime settings for local chat-model creation."""

    quantization_bits: int
    enable_thinking: bool
    reasoning_effort: str
    gguf_params: dict[str, Any]


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    """Resolved request-scoped provider selection for one chat model."""

    provider: str
    model_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 500


def get_db_settings() -> Any:
    """Return persisted LLM generator settings when available."""
    from airunner_services.database.models.llm_generator_settings import (
        LLMGeneratorSettings,
    )

    return LLMGeneratorSettings.objects.first()


def _dtype_to_quantization_bits(dtype: Any) -> int:
    """Map one persisted dtype value to the legacy quantization selector."""
    mapping = {
        "2bit": 2,
        "4bit": 4,
        "8bit": 8,
    }
    return mapping.get(str(dtype or "").strip().lower(), 0)


def get_quantization_bits(db_settings: Any) -> int:
    """Resolve quantization preference from persisted service settings."""
    if db_settings is None:
        return 0

    db_quant = getattr(db_settings, "quantization_bits", None)
    if db_quant is not None:
        try:
            return int(db_quant)
        except (TypeError, ValueError):
            pass

    return _dtype_to_quantization_bits(getattr(db_settings, "dtype", None))


def get_enable_thinking(
    db_settings: Any,
    llm_settings: Any,
) -> bool:
    """Resolve the effective thinking-mode setting."""
    if db_settings is not None and hasattr(db_settings, "enable_thinking"):
        db_value = getattr(db_settings, "enable_thinking", None)
        if db_value is not None:
            return db_value
    return getattr(llm_settings, "enable_thinking", True)


def get_reasoning_effort(
    db_settings: Any,
    llm_settings: Any,
) -> str:
    """Resolve the effective GPT-OSS reasoning-effort setting."""
    allowed = {"low", "medium", "high"}

    if db_settings is not None and hasattr(db_settings, "reasoning_effort"):
        db_value = str(
            getattr(db_settings, "reasoning_effort", "medium") or "medium"
        ).strip().lower()
        if db_value in allowed:
            return db_value

    ui_value = str(
        getattr(llm_settings, "reasoning_effort", "medium") or "medium"
    ).strip().lower()
    if ui_value in allowed:
        return ui_value

    return "medium"


def get_gguf_runtime_params(
    chatbot: Any,
) -> dict[str, Any]:
    """Build llama.cpp generation kwargs from chatbot settings."""
    if not chatbot:
        return {}

    return {
        "max_tokens": getattr(chatbot, "max_new_tokens", 4096),
        "temperature": getattr(chatbot, "temperature", 700) / 10000.0,
        "top_p": getattr(chatbot, "top_p", 900) / 1000.0,
        "top_k": getattr(chatbot, "top_k", 20),
        "repeat_penalty": getattr(
            chatbot,
            "repetition_penalty",
            115,
        )
        / 100.0,
    }


def get_provider_runtime_params(chatbot: Any) -> dict[str, Any]:
    """Build API-provider generation kwargs from chatbot settings."""
    if not chatbot:
        return {
            "temperature": 0.7,
            "max_tokens": 500,
        }

    return {
        "temperature": getattr(chatbot, "temperature", 700) / 10000.0,
        "max_tokens": getattr(chatbot, "max_new_tokens", 500),
    }


def build_provider_runtime_config(
    llm_settings: Any,
    chatbot: Any,
) -> ProviderRuntimeConfig:
    """Return the request-scoped provider selection for model creation."""
    provider_params = get_provider_runtime_params(chatbot)
    if getattr(llm_settings, "use_local_llm", True):
        return _local_provider_runtime(provider_params)
    if getattr(llm_settings, "use_openrouter", False):
        return _openrouter_provider_runtime(llm_settings, provider_params)
    if getattr(llm_settings, "use_ollama", False):
        return _ollama_provider_runtime(llm_settings, provider_params)
    if getattr(llm_settings, "use_openai", False):
        return _openai_provider_runtime(llm_settings, provider_params)
    return _local_provider_runtime(provider_params)


def _local_provider_runtime(
    provider_params: dict[str, Any],
) -> ProviderRuntimeConfig:
    """Build the local provider runtime configuration."""
    return ProviderRuntimeConfig(provider="local", **provider_params)


def _openrouter_provider_runtime(
    llm_settings: Any,
    provider_params: dict[str, Any],
) -> ProviderRuntimeConfig:
    """Build the OpenRouter provider runtime configuration."""
    return ProviderRuntimeConfig(
        provider="openrouter",
        model_name=getattr(
            llm_settings,
            "model",
            "mistralai/mistral-7b-instruct",
        ),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        **provider_params,
    )


def _ollama_provider_runtime(
    llm_settings: Any,
    provider_params: dict[str, Any],
) -> ProviderRuntimeConfig:
    """Build the Ollama provider runtime configuration."""
    return ProviderRuntimeConfig(
        provider="ollama",
        model_name=getattr(llm_settings, "ollama_model", "llama2"),
        base_url=getattr(
            llm_settings,
            "ollama_base_url",
            "http://localhost:11434",
        ),
        **provider_params,
    )


def _openai_provider_runtime(
    llm_settings: Any,
    provider_params: dict[str, Any],
) -> ProviderRuntimeConfig:
    """Build the OpenAI provider runtime configuration."""
    return ProviderRuntimeConfig(
        provider="openai",
        model_name=getattr(llm_settings, "openai_model", "gpt-4"),
        api_key=os.getenv("OPENAI_API_KEY"),
        **provider_params,
    )


def build_local_runtime_config(
    db_settings: Any,
    llm_settings: Any,
    chatbot: Any,
) -> LocalRuntimeConfig:
    """Return the resolved persisted runtime config for local/GGUF loads."""
    return LocalRuntimeConfig(
        quantization_bits=get_quantization_bits(db_settings),
        enable_thinking=get_enable_thinking(db_settings, llm_settings),
        reasoning_effort=get_reasoning_effort(db_settings, llm_settings),
        gguf_params=get_gguf_runtime_params(chatbot),
    )