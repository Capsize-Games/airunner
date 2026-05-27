"""Factory for creating LangChain ChatModel instances based on AI Runner settings."""

from typing import Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel

from airunner_services.llm.adapters.chat_model_factory_creation_helper import (
    create_local_model_from_settings,
    create_provider_model_from_runtime,
)
from airunner_services.llm.adapters.chat_model_factory_helpers import (
    build_provider_runtime_config,
)
from airunner_services.llm.adapters.chat_model_factory_model_builders import (
    create_gguf_model,
    create_ollama_model,
    create_openai_model,
    create_openrouter_model,
)


class ChatModelFactory:
    """
    Factory for creating appropriate LangChain ChatModel instances.

    Supports:
    - GGUF local models via llama.cpp
    - OpenRouter API
    - Ollama
    - OpenAI (future)
    """

    _LOCAL_GGUF_ONLY_MESSAGE = (
        "Local LLM mode requires a GGUF model running through llama.cpp. "
        "Transformers-based local loading and inference are disabled."
    )

    @staticmethod
    def create_gguf_model(
        model_path: str,
        gguf_runtime_profile: Optional[str] = None,
        n_ctx: int = 32768,  # Qwen3 native context (use YaRN for extended)
        n_gpu_layers: int = -1,
        n_batch: int = 256,
        max_tokens: int = 32768,  # Qwen3 recommended output length
        temperature: float = 0.6,  # Qwen3 thinking mode recommended
        top_p: float = 0.95,  # Qwen3 thinking mode recommended
        top_k: int = 20,  # Qwen3 recommended
        repeat_penalty: float = 1.15,
        flash_attn: bool = True,
        enable_thinking: bool = True,
        reasoning_effort: str = "medium",
        tool_calling_mode: str = "native",
        chat_format: Optional[str] = None,
        use_yarn: bool = False,  # Disabled by default - requires more VRAM
        yarn_orig_ctx: int = 32768,  # Qwen3 native context
        preferred_filename: Optional[str] = None,
    ) -> BaseChatModel:
        """Create one GGUF-backed chat model."""
        return create_gguf_model(
            model_path=model_path,
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
            preferred_filename=preferred_filename,
        )

    @staticmethod
    def create_openrouter_model(
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> BaseChatModel:
        """Create one OpenRouter chat model."""
        return create_openrouter_model(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def create_ollama_model(
        model_name: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
    ) -> BaseChatModel:
        """Create one Ollama chat model."""
        return create_ollama_model(
            model_name=model_name,
            base_url=base_url,
            temperature=temperature,
        )

    @staticmethod
    def create_openai_model(
        api_key: str,
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> BaseChatModel:
        """Create one OpenAI chat model."""
        return create_openai_model(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def create_from_settings(
        llm_settings: Any,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        chatbot: Optional[Any] = None,
        model_path: Optional[str] = None,
        gguf_runtime_profile: Optional[str] = None,
    ) -> BaseChatModel:
        """
        Create appropriate ChatModel based on AI Runner settings.

        This method selects the supported runtime backend:
        - Prefer GGUF format for local llama.cpp execution
        - Reuse an existing GGUF when one is already available
        - Reject non-GGUF local execution instead of falling back

        Args:
            llm_settings: LLMSettings instance
            model: Ignored legacy parameter retained for compatibility
            tokenizer: Ignored legacy parameter retained for compatibility
            chatbot: Chatbot settings instance
            model_path: Path to model directory or GGUF artifact

        Returns:
            Appropriate ChatModel instance

        Raises:
            ValueError: If settings are invalid or required components missing
        """
        provider_runtime = build_provider_runtime_config(
            llm_settings,
            chatbot,
        )

        if provider_runtime.provider == "local":
            local_model = create_local_model_from_settings(
                llm_settings=llm_settings,
                chatbot=chatbot,
                model_path=model_path,
                gguf_runtime_profile=gguf_runtime_profile,
                create_gguf_model=ChatModelFactory.create_gguf_model,
            )
            if local_model is not None:
                return local_model
            raise ValueError(ChatModelFactory._LOCAL_GGUF_ONLY_MESSAGE)

        provider_model = create_provider_model_from_runtime(
            provider_runtime=provider_runtime,
            create_openrouter_model=ChatModelFactory.create_openrouter_model,
            create_ollama_model=ChatModelFactory.create_ollama_model,
            create_openai_model=ChatModelFactory.create_openai_model,
        )
        if provider_model is not None:
            return provider_model

        raise ValueError(
            "Unable to create ChatModel: no valid configuration found"
        )
