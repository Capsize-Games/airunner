"""Concrete model-construction helpers for ChatModelFactory."""

from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from airunner_services.downloads.policy import (
    is_openai_allowed,
    is_openrouter_allowed,
)
from airunner_services.llm.adapters.chat_gguf import (
    ChatGGUF,
    find_gguf_file,
)


_DEFAULT_GGUF_MODEL_KWARGS: dict[str, object] = {
    "gguf_runtime_profile": None,
    "n_ctx": 32768,
    "n_gpu_layers": -1,
    "n_batch": 256,
    "max_tokens": 32768,
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "repeat_penalty": 1.15,
    "flash_attn": True,
    "enable_thinking": True,
    "reasoning_effort": "medium",
    "tool_calling_mode": "native",
    "chat_format": None,
    "use_yarn": False,
    "yarn_orig_ctx": 32768,
    "preferred_filename": None,
}


def _resolved_gguf_file(
    model_path: str,
    preferred_filename: Optional[str],
) -> str:
    """Return one resolved GGUF file path or raise when missing."""
    gguf_file = (
        find_gguf_file(model_path, preferred_filename=preferred_filename)
        if not model_path.endswith(".gguf")
        else model_path
    )
    if gguf_file:
        return gguf_file
    raise ValueError(f"No GGUF file found in {model_path}")


def _gguf_model_kwargs(gguf_file: str, **kwargs: object) -> dict[str, object]:
    """Return GGUF model constructor kwargs."""
    kwargs["model_path"] = gguf_file
    return kwargs


def _require_chat_openai() -> type:
    """Return the ChatOpenAI class or raise an installation error."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as error:
        raise ImportError(
            "langchain-openai is required for OpenAI/OpenRouter support. "
            "Install with: pip install langchain-openai"
        ) from error
    return ChatOpenAI


def _raise_if_remote_disabled(service_name: str, allowed: bool) -> None:
    """Raise when a remote model provider is disabled in privacy settings."""
    if allowed:
        return
    raise ValueError(
        f"{service_name} is disabled in privacy settings. "
        "Enable it in Preferences -> Privacy & Security -> External Services."
    )


def create_gguf_model(model_path: str, **kwargs: object) -> ChatGGUF:
    """Create one GGUF-backed chat model."""
    resolved_kwargs = dict(_DEFAULT_GGUF_MODEL_KWARGS)
    resolved_kwargs.update(kwargs)
    preferred_filename = resolved_kwargs.pop("preferred_filename")
    gguf_file = _resolved_gguf_file(model_path, preferred_filename)
    return ChatGGUF(**_gguf_model_kwargs(gguf_file, **resolved_kwargs))


def create_openrouter_model(
    api_key: str,
    model_name: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> BaseChatModel:
    """Create one OpenRouter chat model."""
    _raise_if_remote_disabled("OpenRouter", is_openrouter_allowed())
    chat_openai = _require_chat_openai()
    return chat_openai(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=temperature,
        max_tokens=max_tokens,
    )


def create_ollama_model(
    model_name: str,
    base_url: str = "http://localhost:11434",
    temperature: float = 0.7,
) -> BaseChatModel:
    """Create one Ollama chat model."""
    try:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=temperature,
        )
    except ImportError as error:
        raise ImportError(
            "langchain-ollama is required for Ollama support. "
            "Install with: pip install langchain-ollama"
        ) from error


def create_openai_model(
    api_key: str,
    model_name: str = "gpt-4",
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> BaseChatModel:
    """Create one OpenAI chat model."""
    _raise_if_remote_disabled("OpenAI", is_openai_allowed())
    chat_openai = _require_chat_openai()
    return chat_openai(
        model=model_name,
        openai_api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )