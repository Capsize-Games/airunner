"""Configuration for LLM providers and their available models."""

from typing import Dict, List


class LLMProviderConfig:
    """Available models for each LLM provider."""

    # Local HuggingFace models available for download
    LOCAL_MODELS = {
        "ministral-8b": {
            "name": "Ministral-8B-Instruct-2410",
            "repo_id": "mistralai/Ministral-8B-Instruct-2410",
            "model_type": "mistral",
            "function_calling": True,
            "context_length": 128000,
            "vram_2bit_gb": 4,
            "vram_4bit_gb": 8,
            "vram_8bit_gb": 16,
            "description": "Mistral 8B with function calling support",
        },
        "magistral-small-24b": {
            "name": "Magistral-Small-2509",
            "repo_id": "mistralai/Magistral-Small-2509",
            "model_type": "mistral",
            "function_calling": True,
            "context_length": 128000,
            "vram_2bit_gb": 7,
            "vram_4bit_gb": 14,
            "vram_8bit_gb": 28,
            "description": "Mistral 24B reasoning model with multimodal support, vision, and tool calling",
        },
        "llama-3.2-3b": {
            "name": "Llama-3.2-3B-Instruct",
            "repo_id": "meta-llama/Llama-3.2-3B-Instruct",
            "model_type": "llm",
            "function_calling": False,
            "context_length": 128000,
            "vram_2bit_gb": 2,
            "vram_4bit_gb": 3,
            "vram_8bit_gb": 6,
            "description": "Meta Llama 3.2 3B (no tool calling - for simple chat only)",
        },
        "llama-3.1-8b": {
            "name": "Llama-3.1-8B-Instruct",
            "repo_id": "meta-llama/Llama-3.1-8B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "context_length": 128000,
            "vram_2bit_gb": 3,
            "vram_4bit_gb": 5,
            "vram_8bit_gb": 10,
            "description": "Meta Llama 3.1 8B with function calling",
        },
        "qwen2.5-7b": {
            "name": "Qwen2.5-7B-Instruct",
            "repo_id": "Qwen/Qwen2.5-7B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "context_length": 32768,
            "vram_2bit_gb": 4,
            "vram_4bit_gb": 7,
            "vram_8bit_gb": 14,
            "description": "Qwen 2.5 7B with function calling",
        },
        "llama-4-maverick-17b": {
            "name": "Llama-4-Maverick-17B-128E-Instruct",
            "repo_id": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "context_length": 1000000,
            "vram_2bit_gb": 6,
            "vram_4bit_gb": 12,
            "vram_8bit_gb": 24,
            "description": "Meta Llama 4 Maverick 17B with 128 experts, 1M context, multimodal, and tool calling",
        },
        "custom": {
            "name": "Custom Local Path",
            "repo_id": "",
            "model_type": "llm",
            "function_calling": False,
            "context_length": 0,
            "vram_2bit_gb": 0,
            "vram_4bit_gb": 0,
            "vram_8bit_gb": 0,
            "description": "Use custom model path",
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
