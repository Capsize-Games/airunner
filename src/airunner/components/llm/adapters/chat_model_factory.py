"""Factory for creating LangChain ChatModel instances based on AI Runner settings."""

from typing import Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel

from airunner.components.llm.adapters.chat_huggingface_local import (
    ChatHuggingFaceLocal,
)


class ChatModelFactory:
    """
    Factory for creating appropriate LangChain ChatModel instances.

    Supports:
    - HuggingFace local models (with pre-loaded model+tokenizer)
    - OpenRouter API
    - Ollama
    - OpenAI (future)
    """

    @staticmethod
    def create_local_model(
        model: Any,
        tokenizer: Any,
        model_path: Optional[str] = None,
        max_new_tokens: int = 500,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        repetition_penalty: float = 1.15,
        do_sample: bool = True,
    ) -> ChatHuggingFaceLocal:
        """
        Create a ChatModel for locally-loaded HuggingFace models.

        Args:
            model: Pre-loaded HuggingFace model
            tokenizer: Pre-loaded HuggingFace tokenizer
            model_path: Path to model directory (for Mistral native tokenizer)
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            repetition_penalty: Penalty for repeating tokens
            do_sample: Whether to use sampling

        Returns:
            ChatHuggingFaceLocal instance
        """
        chat_model = ChatHuggingFaceLocal(
            model=model,
            tokenizer=tokenizer,
            model_path=model_path,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=repetition_penalty,
            do_sample=do_sample,
        )

        # Initialize Mistral tokenizer if available
        if model_path:
            chat_model._init_mistral_tokenizer()

        return chat_model

    @staticmethod
    def create_openrouter_model(
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> BaseChatModel:
        """
        Create a ChatModel for OpenRouter API.

        Args:
            api_key: OpenRouter API key
            model_name: Model identifier on OpenRouter
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            ChatOpenAI configured for OpenRouter
        """
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenRouter support. "
                "Install with: pip install langchain-openai"
            )

    @staticmethod
    def create_ollama_model(
        model_name: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
    ) -> BaseChatModel:
        """
        Create a ChatModel for Ollama.

        Args:
            model_name: Ollama model name
            base_url: Ollama server URL
            temperature: Sampling temperature

        Returns:
            ChatOllama instance
        """
        try:
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=model_name,
                base_url=base_url,
                temperature=temperature,
            )
        except ImportError:
            raise ImportError(
                "langchain-ollama is required for Ollama support. "
                "Install with: pip install langchain-ollama"
            )

    @staticmethod
    def create_openai_model(
        api_key: str,
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> BaseChatModel:
        """
        Create a ChatModel for OpenAI API.

        Args:
            api_key: OpenAI API key
            model_name: OpenAI model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            ChatOpenAI instance
        """
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenAI support. "
                "Install with: pip install langchain-openai"
            )

    @staticmethod
    def create_from_settings(
        llm_settings: Any,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        chatbot: Optional[Any] = None,
        model_path: Optional[str] = None,
    ) -> BaseChatModel:
        """
        Create appropriate ChatModel based on AI Runner settings.

        Args:
            llm_settings: LLMSettings instance
            model: Pre-loaded HuggingFace model (for local mode)
            tokenizer: Pre-loaded HuggingFace tokenizer (for local mode)
            chatbot: Chatbot settings instance
            model_path: Path to model directory (for Mistral native tokenizer)

        Returns:
            Appropriate ChatModel instance

        Raises:
            ValueError: If settings are invalid or required components missing
        """
        # Local HuggingFace model
        if getattr(llm_settings, "use_local_llm", True):
            if not model:
                raise ValueError("Local LLM mode requires pre-loaded model")

            # Tokenizer is optional for Mistral3 models (they use mistral_common)
            # For other models, tokenizer is required
            if not tokenizer and not model_path:
                raise ValueError(
                    "Local LLM mode requires either tokenizer or model_path for Mistral3 models"
                )

            # Get generation parameters from chatbot settings
            params = {}
            if chatbot:
                params = {
                    "max_new_tokens": getattr(chatbot, "max_new_tokens", 500),
                    "temperature": getattr(chatbot, "temperature", 700)
                    / 10000.0,
                    "top_p": getattr(chatbot, "top_p", 900) / 1000.0,
                    "top_k": getattr(chatbot, "top_k", 50),
                    "repetition_penalty": getattr(
                        chatbot, "repetition_penalty", 115
                    )
                    / 100.0,
                    "do_sample": getattr(chatbot, "do_sample", True),
                }

            return ChatModelFactory.create_local_model(
                model=model,
                tokenizer=tokenizer,
                model_path=model_path,
                **params
            )

        # OpenRouter
        if getattr(llm_settings, "use_openrouter", False):
            import os

            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY environment variable required for OpenRouter"
                )

            model_name = getattr(
                llm_settings, "model", "mistralai/mistral-7b-instruct"
            )
            temperature = 0.7
            max_tokens = 500

            if chatbot:
                temperature = getattr(chatbot, "temperature", 700) / 10000.0
                max_tokens = getattr(chatbot, "max_new_tokens", 500)

            return ChatModelFactory.create_openrouter_model(
                api_key=api_key,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Ollama
        if getattr(llm_settings, "use_ollama", False):
            model_name = getattr(llm_settings, "ollama_model", "llama2")
            base_url = getattr(
                llm_settings, "ollama_base_url", "http://localhost:11434"
            )
            temperature = 0.7

            if chatbot:
                temperature = getattr(chatbot, "temperature", 700) / 10000.0

            return ChatModelFactory.create_ollama_model(
                model_name=model_name,
                base_url=base_url,
                temperature=temperature,
            )

        # OpenAI (future)
        if getattr(llm_settings, "use_openai", False):
            import os

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable required for OpenAI"
                )

            model_name = getattr(llm_settings, "openai_model", "gpt-4")
            temperature = 0.7
            max_tokens = 500

            if chatbot:
                temperature = getattr(chatbot, "temperature", 700) / 10000.0
                max_tokens = getattr(chatbot, "max_new_tokens", 500)

            return ChatModelFactory.create_openai_model(
                api_key=api_key,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Default to local if nothing else specified
        if model and tokenizer:
            return ChatModelFactory.create_local_model(
                model=model, tokenizer=tokenizer, model_path=model_path
            )

        raise ValueError(
            "Unable to create ChatModel: no valid configuration found"
        )
