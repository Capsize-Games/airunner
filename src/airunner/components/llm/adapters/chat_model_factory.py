"""Factory for creating LangChain ChatModel instances based on AI Runner settings."""

from typing import Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel

from airunner.components.llm.adapters.chat_huggingface_local import (
    ChatHuggingFaceLocal,
)
from airunner.components.llm.adapters.chat_gguf import (
    ChatGGUF,
    UnsupportedGGUFArchitectureError,
    find_gguf_file,
    is_gguf_model,
)
from airunner.utils.model_optimizer import get_model_optimizer


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
        top_k: int = 20,  # Qwen3 recommended value
        repetition_penalty: float = 1.15,
        do_sample: bool = True,
        enable_thinking: bool = True,
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
            enable_thinking: Enable Qwen3 thinking mode (<think>...</think>)

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
            enable_thinking=enable_thinking,
        )

        # Initialize Mistral tokenizer if available
        if model_path:
            chat_model._init_mistral_tokenizer()

        return chat_model

    @staticmethod
    def create_gguf_model(
        model_path: str,
        n_ctx: int = 32768,  # Qwen3 native context (use YaRN for extended)
        n_gpu_layers: int = -1,
        n_batch: int = 512,
        max_tokens: int = 32768,  # Qwen3 recommended output length
        temperature: float = 0.6,  # Qwen3 thinking mode recommended
        top_p: float = 0.95,  # Qwen3 thinking mode recommended
        top_k: int = 20,  # Qwen3 recommended
        repeat_penalty: float = 1.15,
        flash_attn: bool = True,
        enable_thinking: bool = True,
        use_yarn: bool = False,  # Disabled by default - requires more VRAM
        yarn_orig_ctx: int = 32768,  # Qwen3 native context
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
            use_yarn: Enable YaRN for extended context (requires more VRAM)
            yarn_orig_ctx: Original context length for YaRN scaling

        Returns:
            ChatGGUF instance
        """
        # If model_path is a directory, find the GGUF file
        gguf_file = find_gguf_file(model_path) if not model_path.endswith(".gguf") else model_path

        if not gguf_file:
            raise ValueError(f"No GGUF file found in {model_path}")

        return ChatGGUF(
            model_path=gguf_file,
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
        # Check if OpenRouter is allowed in privacy settings
        from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
            is_openrouter_allowed,
        )
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
        # Check if OpenAI is allowed in privacy settings
        from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
            is_openai_allowed,
        )
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
    def create_from_settings(
        llm_settings: Any,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        chatbot: Optional[Any] = None,
        model_path: Optional[str] = None,
    ) -> BaseChatModel:
        """
        Create appropriate ChatModel based on AI Runner settings.

        This method intelligently selects the best model format:
        - If quantization_bits=0 (GGUF), prefer GGUF format
        - If GGUF file exists, use it even if not explicitly requested
        - Otherwise, use SafeTensors with BitsAndBytes quantization

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
        # Get quantization preference from settings
        # Default to GGUF (0) - GGUF is the only supported quantization format
        from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings
        from airunner.utils.settings.get_qsettings import get_qsettings
        
        db_settings = LLMGeneratorSettings.objects.first()
        quantization_bits = 0  # Default to GGUF
        
        # Check QSettings first (UI preference)
        try:
            qs = get_qsettings()
            saved = qs.value("llm_settings/quantization_bits", None)
            if saved is not None:
                quantization_bits = int(saved)
        except Exception:
            pass
        
        # Database setting overrides if present
        if db_settings is not None:
            db_quant = getattr(db_settings, "quantization_bits", None)
            if db_quant is not None:
                quantization_bits = db_quant
        
        optimizer = get_model_optimizer()
        
        # Check for GGUF model - either explicitly requested or already available
        if model_path:
            # User explicitly wants GGUF (quantization_bits=0)
            use_gguf = quantization_bits == 0
            
            # Also check if GGUF is available even if not explicitly requested
            existing_gguf = optimizer.find_existing_gguf(model_path)
            
            if use_gguf or existing_gguf or is_gguf_model(model_path):
                # Determine which GGUF file to use
                gguf_path = existing_gguf or model_path
                
                # If user wants GGUF but no GGUF exists, try to convert
                if use_gguf and not existing_gguf and not is_gguf_model(model_path):
                    quant_type = optimizer.bits_to_gguf_quantization(quantization_bits)
                    converted = optimizer.ensure_gguf(model_path, quant_type)
                    if converted:
                        gguf_path = converted
                    else:
                        # Fall through to SafeTensors if conversion not possible
                        pass
                
                # Only use GGUF if we have a valid path
                if gguf_path and (is_gguf_model(gguf_path) or optimizer.find_existing_gguf(gguf_path)):
                    # Get generation parameters from chatbot settings
                    params = {}
                    if chatbot:
                        params = {
                            "max_tokens": getattr(chatbot, "max_new_tokens", 4096),
                            "temperature": getattr(chatbot, "temperature", 700) / 10000.0,
                            "top_p": getattr(chatbot, "top_p", 900) / 1000.0,
                            "top_k": getattr(chatbot, "top_k", 20),
                            "repeat_penalty": getattr(chatbot, "repetition_penalty", 115) / 100.0,
                        }

                    # Get enable_thinking from database
                    enable_thinking = True
                    if db_settings is not None and hasattr(db_settings, "enable_thinking"):
                        db_value = getattr(db_settings, "enable_thinking", None)
                        if db_value is not None:
                            enable_thinking = db_value

                    try:
                        return ChatModelFactory.create_gguf_model(
                            model_path=gguf_path,
                            enable_thinking=enable_thinking,
                            **params
                        )
                    except UnsupportedGGUFArchitectureError as e:
                        # GGUF model architecture not supported by llama-cpp-python
                        # This can happen with very new models like Ministral 3
                        # Raise with clear message - caller must provide transformers model
                        raise ValueError(
                            f"GGUF model architecture '{e.architecture}' is not yet supported by llama-cpp-python. "
                            f"The model '{e.model_path}' requires a newer version of llama-cpp-python. "
                            "Please try a different model or wait for llama-cpp-python to add support."
                        ) from e

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

            # Get enable_thinking from database (LLMGeneratorSettings) first,
            # then fall back to llm_settings dataclass, then default to True
            from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings
            db_settings = LLMGeneratorSettings.objects.first()
            enable_thinking = True  # Default
            if db_settings is not None and hasattr(db_settings, "enable_thinking"):
                db_value = getattr(db_settings, "enable_thinking", None)
                if db_value is not None:
                    enable_thinking = db_value
                else:
                    # Fall back to llm_settings dataclass
                    enable_thinking = getattr(llm_settings, "enable_thinking", True)
            else:
                enable_thinking = getattr(llm_settings, "enable_thinking", True)

            return ChatModelFactory.create_local_model(
                model=model,
                tokenizer=tokenizer,
                model_path=model_path,
                enable_thinking=enable_thinking,
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
