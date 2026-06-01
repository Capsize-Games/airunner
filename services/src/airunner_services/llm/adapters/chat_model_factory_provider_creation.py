"""Provider-backed chat model creation helpers."""

from __future__ import annotations

from typing import Callable

from langchain_core.language_models.chat_models import BaseChatModel

from airunner_services.llm.adapters.chat_model_factory_helpers import (
    ProviderRuntimeConfig,
)


def create_provider_model_from_runtime(
    provider_runtime: ProviderRuntimeConfig,
    create_openrouter_model: Callable[..., BaseChatModel],
    create_ollama_model: Callable[..., BaseChatModel],
    create_openai_model: Callable[..., BaseChatModel],
) -> BaseChatModel | None:
    """Create one non-local chat model from the resolved provider runtime."""
    if provider_runtime.provider == "openrouter":
        return _create_openrouter_runtime(
            provider_runtime,
            create_openrouter_model,
        )
    if provider_runtime.provider == "ollama":
        return _create_ollama_runtime(provider_runtime, create_ollama_model)
    if provider_runtime.provider == "openai":
        return _create_openai_runtime(provider_runtime, create_openai_model)
    return None


def _create_openrouter_runtime(
    provider_runtime: ProviderRuntimeConfig,
    create_openrouter_model: Callable[..., BaseChatModel],
) -> BaseChatModel:
    """Create one OpenRouter-backed model from provider runtime config."""
    api_key = _require_provider_api_key(
        provider_runtime.api_key,
        "OPENROUTER_API_KEY environment variable required for OpenRouter",
    )
    return create_openrouter_model(
        api_key=api_key,
        model_name=provider_runtime.model_name or "mistralai/mistral-7b-instruct",
        temperature=provider_runtime.temperature,
        max_tokens=provider_runtime.max_tokens,
    )


def _create_ollama_runtime(
    provider_runtime: ProviderRuntimeConfig,
    create_ollama_model: Callable[..., BaseChatModel],
) -> BaseChatModel:
    """Create one Ollama-backed model from provider runtime config."""
    return create_ollama_model(
        model_name=provider_runtime.model_name or "llama2",
        base_url=provider_runtime.base_url or "http://localhost:11434",
        temperature=provider_runtime.temperature,
    )


def _create_openai_runtime(
    provider_runtime: ProviderRuntimeConfig,
    create_openai_model: Callable[..., BaseChatModel],
) -> BaseChatModel:
    """Create one OpenAI-backed model from provider runtime config."""
    api_key = _require_provider_api_key(
        provider_runtime.api_key,
        "OPENAI_API_KEY environment variable required for OpenAI",
    )
    return create_openai_model(
        api_key=api_key,
        model_name=provider_runtime.model_name or "gpt-4",
        temperature=provider_runtime.temperature,
        max_tokens=provider_runtime.max_tokens,
    )


def _require_provider_api_key(api_key: str | None, message: str) -> str:
    """Return one provider API key or raise a clear configuration error."""
    if api_key:
        return api_key
    raise ValueError(message)