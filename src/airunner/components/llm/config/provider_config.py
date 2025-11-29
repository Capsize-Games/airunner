"""Configuration for LLM providers and their available models.

GGUF Support:
    Models can specify `gguf_repo_id` and `gguf_filename` for GGUF format downloads.
    GGUF models are smaller and faster than BitsAndBytes quantized safetensors:
    - Q4_K_M: ~4.1GB for 7B model (vs ~5.5GB for BnB 4-bit)
    - Faster inference via optimized llama.cpp backend
    
    When a model has GGUF config and user selects GGUF quantization,
    the downloader will fetch the single .gguf file instead of safetensors.
"""

from typing import Dict, List, Optional


class LLMProviderConfig:
    """Available models for each LLM provider."""

    # Local HuggingFace models available for download
    # Models can have optional GGUF variants via gguf_repo_id and gguf_filename
    LOCAL_MODELS = {
        "ministral-8b": {
            "name": "Ministral-8B-Instruct-2410",
            "repo_id": "mistralai/Ministral-8B-Instruct-2410",
            "model_type": "mistral",
            "function_calling": True,
            "tool_calling_mode": "native",  # Uses tekken.json tokenizer
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 128000,
            "vram_2bit_gb": 4,
            "vram_4bit_gb": 8,
            "vram_8bit_gb": 16,
            "description": "Mistral 8B with native function calling support",
            # GGUF variant (bartowski's quantizations are high quality)
            "gguf_repo_id": "bartowski/Ministral-8B-Instruct-2410-GGUF",
            "gguf_filename": "Ministral-8B-Instruct-2410-Q4_K_M.gguf",
        },
        "magistral-small-24b": {
            "name": "Magistral-Small-2509",
            "repo_id": "mistralai/Magistral-Small-2509",
            "model_type": "mistral",
            "function_calling": True,
            "tool_calling_mode": "native",  # Uses tekken.json tokenizer
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": True,  # Has multimodal/vision support
            "code_capable": True,
            "context_length": 128000,
            "vram_2bit_gb": 7,
            "vram_4bit_gb": 14,
            "vram_8bit_gb": 28,
            "description": "Mistral 24B reasoning model with multimodal support, vision, and native tool calling",
            # GGUF variant
            "gguf_repo_id": "bartowski/Magistral-Small-2509-GGUF",
            "gguf_filename": "Magistral-Small-2509-Q4_K_M.gguf",
        },
        "llama-3.2-3b": {
            "name": "Llama-3.2-3B-Instruct",
            "repo_id": "meta-llama/Llama-3.2-3B-Instruct",
            "model_type": "llm",
            "function_calling": False,
            "tool_calling_mode": "react",  # Fallback pattern only
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": False,
            "context_length": 128000,
            "vram_2bit_gb": 2,
            "vram_4bit_gb": 3,
            "vram_8bit_gb": 6,
            "description": "Meta Llama 3.2 3B (ReAct pattern only - for simple chat)",
            # GGUF variant
            "gguf_repo_id": "bartowski/Llama-3.2-3B-Instruct-GGUF",
            "gguf_filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        },
        "llama-3.1-8b": {
            "name": "Llama-3.1-8B-Instruct",
            "repo_id": "meta-llama/Llama-3.1-8B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",  # Structured JSON output
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 128000,
            "vram_2bit_gb": 3,
            "vram_4bit_gb": 5,
            "vram_8bit_gb": 10,
            "description": "Meta Llama 3.1 8B with structured JSON tool calling",
            # GGUF variant
            "gguf_repo_id": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
            "gguf_filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        },
        "qwen2.5-7b": {
            "name": "Qwen2.5-7B-Instruct",
            "repo_id": "Qwen/Qwen2.5-7B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",  # Structured JSON output (Hermes-style compatible)
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 131072,  # 128K tokens (full context with YaRN scaling)
            "vram_2bit_gb": 4,
            "vram_4bit_gb": 7,
            "vram_8bit_gb": 14,
            "description": "Qwen 2.5 7B with Hermes-style JSON tool calling",
            # GGUF variant (official Qwen GGUF)
            "gguf_repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
            "gguf_filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
        },
        "qwen3-8b": {
            "name": "Qwen3-8B",
            "repo_id": "Qwen/Qwen3-8B",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",  # Structured JSON output
            "supports_thinking": True,  # Qwen3 thinking mode (<think>...</think>)
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 32768,  # 32K native, 131K with YaRN
            "vram_2bit_gb": 5,
            "vram_4bit_gb": 8,
            "vram_8bit_gb": 16,
            "description": "Qwen3 8B with built-in reasoning (thinking mode) and superior agent capabilities",
            # GGUF variant (official Qwen GGUF)
            "gguf_repo_id": "Qwen/Qwen3-8B-GGUF",
            "gguf_filename": "Qwen3-8B-Q4_K_M.gguf",
        },
        "llama-4-maverick-17b": {
            "name": "Llama-4-Maverick-17B-128E-Instruct",
            "repo_id": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",  # Structured JSON output
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": True,  # Multimodal
            "code_capable": True,
            "context_length": 1000000,
            "vram_2bit_gb": 6,
            "vram_4bit_gb": 12,
            "vram_8bit_gb": 24,
            "description": "Meta Llama 4 Maverick 17B with 128 experts, 1M context, multimodal, and JSON tool calling",
            # GGUF variant (bartowski's quantization)
            "gguf_repo_id": "bartowski/Llama-4-Maverick-17B-128E-Instruct-GGUF",
            "gguf_filename": "Llama-4-Maverick-17B-128E-Instruct-Q4_K_M.gguf",
        },
        "custom": {
            "name": "Custom Local Path",
            "repo_id": "",
            "model_type": "llm",
            "function_calling": False,
            "tool_calling_mode": "react",  # Auto-detect or fallback
            "supports_thinking": False,
            "rag_capable": True,  # Assume basic RAG works
            "vision_capable": False,
            "code_capable": False,
            "context_length": 0,
            "vram_2bit_gb": 0,
            "vram_4bit_gb": 0,
            "vram_8bit_gb": 0,
            "description": "Use custom model path (auto-detects tool calling mode)",
        },
    }

    # OpenRouter models (common ones)
    OPENROUTER_MODELS = [
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-opus",
        "openai/gpt-4-turbo",
        "openai/gpt-4",
        "openai/gpt-3.5-turbo",
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.1-8b-instruct",
        "google/gemini-pro-1.5",
        "mistralai/mistral-large",
        "custom",
    ]

    # Ollama models (common ones)
    OLLAMA_MODELS = [
        "llama3.2",
        "llama3.1",
        "llama3",
        "mistral",
        "mixtral",
        "phi3",
        "qwen2.5",
        "gemma2",
        "codellama",
        "custom",
    ]

    @classmethod
    def get_models_for_provider(cls, provider: str) -> List[str]:
        """
        Get list of model names for a given provider.

        Args:
            provider: "local", "openrouter", or "ollama"

        Returns:
            List of model identifiers
        """
        if provider == "local":
            return list(cls.LOCAL_MODELS.keys())
        elif provider == "openrouter":
            return cls.OPENROUTER_MODELS
        elif provider == "ollama":
            return cls.OLLAMA_MODELS
        return []

    @classmethod
    def get_model_display_name(cls, provider: str, model_id: str) -> str:
        """
        Get human-readable display name for a model.

        Args:
            provider: Provider name
            model_id: Model identifier

        Returns:
            Display name for the model
        """
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            if model_info["function_calling"]:
                return f"{model_info['name']} ⚡"
            return f"{model_info['name']}"
        return model_id

    @classmethod
    def get_model_info(cls, provider: str, model_id: str) -> Dict:
        """
        Get detailed information about a model.

        Args:
            provider: Provider name
            model_id: Model identifier

        Returns:
            Dict with model information
        """
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            return cls.LOCAL_MODELS[model_id]
        return {}

    @classmethod
    def get_vram_for_quantization(
        cls, provider: str, model_id: str, quantization_bits: int
    ) -> int:
        """
        Get estimated VRAM usage for a model at a specific quantization level.

        Args:
            provider: Provider name
            model_id: Model identifier
            quantization_bits: 2, 4, or 8

        Returns:
            Estimated VRAM in GB
        """
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            vram_key = f"vram_{quantization_bits}bit_gb"
            return model_info.get(vram_key, 0)
        return 0

    @classmethod
    def requires_download(cls, provider: str, model_id: str) -> bool:
        """
        Check if model needs to be downloaded.

        Args:
            provider: Provider name
            model_id: Model identifier

        Returns:
            True if model needs download
        """
        return provider == "local" and model_id != "custom"

    @classmethod
    def has_gguf_support(cls, provider: str, model_id: str) -> bool:
        """
        Check if model has GGUF support for the given provider.

        Args:
            provider: Provider name
            model_id: Model identifier

        Returns:
            True if GGUF variant is available
        """
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            return bool(model_info.get("gguf_repo_id") and model_info.get("gguf_filename"))
        return False

    @classmethod
    def has_gguf_variant(cls, model_id: str) -> bool:
        """
        Check if model has a GGUF variant available.

        Args:
            model_id: Model identifier

        Returns:
            True if GGUF variant is available
        """
        if model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            return bool(model_info.get("gguf_repo_id") and model_info.get("gguf_filename"))
        return False

    @classmethod
    def get_gguf_info(cls, provider: str, model_id: str) -> Optional[Dict[str, str]]:
        """
        Get GGUF download info for a model.

        Args:
            provider: Provider name
            model_id: Model identifier

        Returns:
            Dict with repo_id and filename, or None
        """
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            repo_id = model_info.get("gguf_repo_id")
            filename = model_info.get("gguf_filename")
            if repo_id and filename:
                return {
                    "repo_id": repo_id,
                    "filename": filename,
                }
        return None
