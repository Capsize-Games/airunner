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


def create_gguf_model(
    model_path: str,
    gguf_runtime_profile: Optional[str] = None,
    n_ctx: int = 32768,
    n_gpu_layers: int = -1,
    n_batch: int = 256,
    max_tokens: int = 32768,
    temperature: float = 0.6,
    top_p: float = 0.95,
    top_k: int = 20,
    repeat_penalty: float = 1.15,
    flash_attn: bool = True,
    enable_thinking: bool = True,
    reasoning_effort: str = "medium",
    tool_calling_mode: str = "native",
    chat_format: Optional[str] = None,
    use_yarn: bool = False,
    yarn_orig_ctx: int = 32768,
    preferred_filename: Optional[str] = None,
) -> ChatGGUF:
    """Create one GGUF-backed chat model."""
    gguf_file = (
        find_gguf_file(model_path, preferred_filename=preferred_filename)
        if not model_path.endswith(".gguf")
        else model_path
    )
    if not gguf_file:
        raise ValueError(f"No GGUF file found in {model_path}")

    return ChatGGUF(
        model_path=gguf_file,
        gguf_runtime_profile=gguf_runtime_profile,
        n_ctx=n_ctx,
        n_gpu_layers=n_gpu_layers,
        n_batch=n_batch,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        repeat_penalty=repeat_penalty,
        flash_attn=flash_attn,
        enable_thinking=enable_thinking,
        reasoning_effort=reasoning_effort,
        tool_calling_mode=tool_calling_mode,
        chat_format=chat_format,
        use_yarn=use_yarn,
        yarn_orig_ctx=yarn_orig_ctx,
    )


def create_openrouter_model(
    api_key: str,
    model_name: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> BaseChatModel:
    """Create one OpenRouter chat model."""
    if not is_openrouter_allowed():
        raise ValueError(
            "OpenRouter is disabled in privacy settings. "
            "Enable it in Preferences → Privacy & Security → External Services."
        )

    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except ImportError as error:
        raise ImportError(
            "langchain-openai is required for OpenRouter support. "
            "Install with: pip install langchain-openai"
        ) from error


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
    if not is_openai_allowed():
        raise ValueError(
            "OpenAI is disabled in privacy settings. "
            "Enable it in Preferences → Privacy & Security → External Services."
        )

    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except ImportError as error:
        raise ImportError(
            "langchain-openai is required for OpenAI support. "
            "Install with: pip install langchain-openai"
        ) from error