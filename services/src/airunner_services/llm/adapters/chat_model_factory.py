"""Factory for creating LangChain ChatModel instances based on AI Runner settings."""

import os
from typing import Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel

from airunner_services.llm.adapters.chat_gguf import (
    ChatGGUF,
    UnsupportedGGUFArchitectureError,
    find_gguf_file,
    is_gguf_model,
)
from airunner_services.llm.adapters.chat_model_factory_helpers import (
    get_chatbot_params,
    get_db_settings,
    get_enable_thinking,
    get_quantization_bits,
    get_reasoning_effort,
)
from airunner_services.llm.config.provider_access_policy import (
    is_openai_allowed,
    is_openrouter_allowed,
)
from airunner_services.llm.config.provider_config import LLMProviderConfig
from airunner_services.utils.model_optimizer import get_model_optimizer


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
    ) -> ChatGGUF:
        """
        Create a ChatModel for GGUF models via llama-cpp-python.

        GGUF models are smaller and faster than BitsAndBytes quantized models:
        - Q4_K_M: ~4.1GB for 7B model (vs ~5.5GB for BnB 4-bit)
        - Faster inference via optimized llama.cpp backend
        - Native GPU acceleration via cuBLAS
        - YaRN support for extended context (opt-in, requires VRAM)

        Args:
            model_path: Path to GGUF model file or directory containing GGUF
            gguf_runtime_profile: Named runtime profile applied to this load
            n_ctx: Context window size (default: 32768 native Qwen3)
            n_gpu_layers: Layers to offload to GPU (-1 for all)
            n_batch: Batch size for prompt processing
            max_tokens: Maximum tokens to generate (32768 for Qwen3)
            temperature: Sampling temperature (0.6 for Qwen3 thinking mode)
            top_p: Nucleus sampling parameter (0.95 for Qwen3 thinking mode)
            top_k: Top-k sampling parameter (20 for Qwen3)
            repeat_penalty: Penalty for repeating tokens
            flash_attn: Use flash attention to reduce VRAM usage
            enable_thinking: Enable thinking mode (Qwen3-style)
            reasoning_effort: GPT-OSS reasoning effort (low, medium, high)
            tool_calling_mode: Tool calling strategy (native, json, react)
            chat_format: Optional llama.cpp chat format override
            use_yarn: Enable YaRN for extended context (requires more VRAM)
            yarn_orig_ctx: Original context length for YaRN scaling
            preferred_filename: Preferred GGUF filename when model_path is a directory

        Returns:
            ChatGGUF instance
        """
        # If model_path is a directory, find the GGUF file
        gguf_file = (
            find_gguf_file(
                model_path,
                preferred_filename=preferred_filename,
            )
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
            
        Raises:
            ValueError: If OpenRouter is disabled in privacy settings
            ImportError: If langchain-openai is not installed
        """
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
            
        Raises:
            ValueError: If OpenAI is disabled in privacy settings
            ImportError: If langchain-openai is not installed
        """
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
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenAI support. "
                "Install with: pip install langchain-openai"
            )

    @staticmethod
    def _resolve_local_model_id(
        db_settings: Any,
        model_path: Optional[str],
    ) -> Optional[str]:
        """Resolve a local model identifier from settings or model path."""
        if not model_path:
            model_id = (
                getattr(db_settings, "model_id", None)
                if db_settings
                else None
            )
            return model_id or None

        resolved_from_path = LLMProviderConfig.resolve_model_id(
            "local",
            os.path.basename(str(model_path)),
        )
        if resolved_from_path:
            return resolved_from_path

        model_id = getattr(db_settings, "model_id", None) if db_settings else None
        return model_id or None

    @staticmethod
    def _get_local_gguf_runtime_params(
        model_id: Optional[str],
        profile_name: Optional[str] = None,
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
        db_settings = get_db_settings()
        quantization_bits = get_quantization_bits(db_settings)
        optimizer = get_model_optimizer()
        resolved_model_id = ChatModelFactory._resolve_local_model_id(
            db_settings,
            model_path,
        )
        
        # Check for GGUF model - either explicitly requested or already available
        if model_path:
            # User explicitly wants GGUF (quantization_bits=0)
            use_gguf = quantization_bits == 0

            preferred_gguf_path = None
            gguf_info = None
            if db_settings is not None:
                model_id = getattr(db_settings, "model_id", None)
                if model_id:
                    gguf_info = LLMProviderConfig.get_gguf_info("local", model_id)
                if gguf_info and not str(model_path).endswith(".gguf"):
                    candidate = os.path.join(model_path, gguf_info["filename"])
                    if os.path.exists(candidate):
                        preferred_gguf_path = candidate

            # Also check if GGUF is available even if not explicitly requested
            allow_generic_directory_scan = gguf_info is None or str(model_path).endswith(
                ".gguf"
            )
            generic_existing_gguf = (
                optimizer.find_existing_gguf(model_path)
                if allow_generic_directory_scan
                else None
            )
            existing_gguf = preferred_gguf_path or generic_existing_gguf
            generic_gguf_available = (
                is_gguf_model(model_path) if allow_generic_directory_scan else False
            )

            if use_gguf or existing_gguf or generic_gguf_available:
                # Determine which GGUF file to use
                gguf_path = existing_gguf or model_path
                
                # If user wants GGUF but no GGUF exists, try to convert
                if use_gguf and not existing_gguf and not generic_gguf_available:
                    quant_type = optimizer.bits_to_gguf_quantization(quantization_bits)
                    converted = optimizer.ensure_gguf(model_path, quant_type)
                    if converted:
                        gguf_path = converted
                    else:
                        # Fall through to SafeTensors if conversion not possible
                        pass
                
                # Only use GGUF if we have a valid path
                has_valid_gguf_path = bool(
                    gguf_path and (
                        str(gguf_path).endswith(".gguf")
                        or (
                            allow_generic_directory_scan
                            and (
                                is_gguf_model(gguf_path)
                                or optimizer.find_existing_gguf(gguf_path)
                            )
                        )
                    )
                )
                if has_valid_gguf_path:
                    params = get_chatbot_params(chatbot, local_mode=False)
                    resolved_model_id = (
                        resolved_model_id
                        or ChatModelFactory._resolve_local_model_id(
                            None,
                            gguf_path,
                        )
                    )
                    params.update(
                        ChatModelFactory._get_local_gguf_runtime_params(
                            resolved_model_id,
                            profile_name=gguf_runtime_profile,
                        )
                    )
                    model_info = (
                        LLMProviderConfig.get_model_info(
                            "local",
                            resolved_model_id,
                        )
                        or {}
                    )
                    enable_thinking = get_enable_thinking(
                        db_settings,
                        llm_settings,
                    )
                    reasoning_effort = get_reasoning_effort(
                        db_settings,
                        llm_settings,
                    )

                    try:
                        return ChatModelFactory.create_gguf_model(
                            model_path=gguf_path,
                            preferred_filename=model_info.get(
                                "gguf_filename",
                            ),
                            gguf_runtime_profile=gguf_runtime_profile,
                            enable_thinking=enable_thinking,
                            reasoning_effort=reasoning_effort,
                            tool_calling_mode=model_info.get(
                                "tool_calling_mode",
                                "native",
                            ),
                            **params
                        )
                    except UnsupportedGGUFArchitectureError as e:
                        version_message = ""
                        if getattr(e, "runtime_version", None):
                            version_message = (
                                f" Installed version: {e.runtime_version}."
                            )
                        raise ValueError(
                            f"GGUF model architecture '{e.architecture}' is "
                            "not yet supported by the installed "
                            "llama-cpp-python runtime."
                            f"{version_message} The model '{e.model_path}' "
                            "requires a newer version of llama-cpp-python "
                            "or a different GGUF build."
                        ) from e

        if getattr(llm_settings, "use_local_llm", True):
            raise ValueError(ChatModelFactory._LOCAL_GGUF_ONLY_MESSAGE)

        # OpenRouter
        if getattr(llm_settings, "use_openrouter", False):
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

        raise ValueError(
            "Unable to create ChatModel: no valid configuration found"
        )
