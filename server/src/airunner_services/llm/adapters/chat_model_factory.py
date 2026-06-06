"""Factory for creating LangChain ChatModel instances based on AI Runner settings."""

from typing import Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel

from airunner_services.llm.adapters.chat_model_factory_creation_helper import (
    create_local_model_from_settings,
)
from airunner_services.llm.adapters.chat_model_factory_provider_creation import (
    create_provider_model_from_runtime,
)
from airunner_services.llm.adapters.chat_model_factory_helpers import (
    build_provider_runtime_config,
)
from airunner_services.llm.adapters.chat_model_factory_model_builders import (
    create_gguf_model as _create_gguf_model,
    create_ollama_model as _create_ollama_model,
    create_openai_model as _create_openai_model,
    create_openrouter_model as _create_openrouter_model,
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
    create_gguf_model = staticmethod(_create_gguf_model)
    create_openrouter_model = staticmethod(_create_openrouter_model)
    create_ollama_model = staticmethod(_create_ollama_model)
    create_openai_model = staticmethod(_create_openai_model)

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
        provider_runtime = build_provider_runtime_config(llm_settings, chatbot)
        if provider_runtime.provider == "local":
            return _create_local_model_from_runtime(
                llm_settings, chatbot, model_path, gguf_runtime_profile
            )
        return _create_provider_model_from_runtime(
            provider_runtime=provider_runtime,
            create_openrouter_model=ChatModelFactory.create_openrouter_model,
            create_ollama_model=ChatModelFactory.create_ollama_model,
            create_openai_model=ChatModelFactory.create_openai_model,
        )


def _create_local_model_from_runtime(
    llm_settings: Any,
    chatbot: Any,
    model_path: Optional[str],
    gguf_runtime_profile: Optional[str],
) -> BaseChatModel:
    """Create one supported local GGUF model or raise a clear error."""
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


def _create_provider_model_from_runtime(
    provider_runtime: Any,
    create_openrouter_model: Any,
    create_ollama_model: Any,
    create_openai_model: Any,
) -> BaseChatModel:
    """Create one provider-backed model or raise when no runtime matched."""
    provider_model = create_provider_model_from_runtime(
        provider_runtime=provider_runtime,
        create_openrouter_model=create_openrouter_model,
        create_ollama_model=create_ollama_model,
        create_openai_model=create_openai_model,
    )
    if provider_model is not None:
        return provider_model
    raise ValueError(
        "Unable to create ChatModel: no valid configuration found"
    )
