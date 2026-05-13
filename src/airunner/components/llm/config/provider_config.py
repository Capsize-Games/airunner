"""Configuration for LLM providers and their available models.

GGUF Support:
    Models can specify `gguf_repo_id` and `gguf_filename` for GGUF format downloads.
    GGUF models are smaller and faster than BitsAndBytes quantized safetensors:
    - Q4_K_M: ~4.1GB for 7B model (vs ~5.5GB for BnB 4-bit)
    - Faster inference via optimized llama.cpp backend
    
    When a model has GGUF config and user selects GGUF quantization,
    the downloader will fetch the single .gguf file instead of safetensors.
"""

import os
from typing import Any, Dict, List, Optional


class LLMProviderConfig:
    """Available models for each LLM provider."""

    _SUPPORTED_LOCAL_MODEL_IDS = (
        "qwen3-8b",
        "qwen3.5-9b",
        "gpt-oss-20b",
        "custom",
    )

    # Local HuggingFace models available for download
    # Models can have optional GGUF variants via gguf_repo_id and gguf_filename
    LOCAL_MODELS = {
        "ministral3-8b": {
            "name": "Ministral-3-8B-Instruct-2512-BF16",
            # Use BF16 version - the standard FP8 version cannot be requantized with BitsAndBytes
            # (FP8 tensors are incompatible with 4-bit quantization)
            "repo_id": "mistralai/Ministral-3-8B-Instruct-2512-BF16",
            "model_type": "ministral3",
            "function_calling": True,
            # NOTE: Changed from "native" to "react" - mistral_common tekken tokenizer
            # produces corrupted output with Mistral3ForConditionalGeneration (vision model)
            "tool_calling_mode": "react",
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": True,  # Ministral 3 has vision capabilities
            "code_capable": True,
            "context_length": 262144,  # 256K context window
            "vram_2bit_gb": 4,
            "vram_4bit_gb": 8,
            "vram_8bit_gb": 18,  # BF16 is ~17.8GB, requires 24GB for full precision
            "description": "Ministral 3 8B with vision, native function calling, and 256K context",
            # IMPORTANT: Config files need patching after download (see ministral3_config_patcher.py):
            # - config.json: text_config.model_type "ministral3" -> "mistral"
            # - tokenizer_config.json: tokenizer_class and extra_special_tokens fixes
            "requires_config_patch": True,
            # NOTE: GGUF disabled - llama-cpp-python 0.3.16 doesn't support mistral3 architecture yet
            # Official GGUF exists at mistralai/Ministral-3-8B-Instruct-2512-GGUF (5.2GB Q4_K_M)
            # Re-enable when llama-cpp-python adds mistral3 support
            # "gguf_repo_id": "mistralai/Ministral-3-8B-Instruct-2512-GGUF",
            # "gguf_filename": "Ministral-3-8B-Instruct-2512-Q4_K_M.gguf",
        },
        "ministral3-8b-reasoning": {
            "name": "Ministral-3-8B-Reasoning-2512",
            "repo_id": "mistralai/Ministral-3-8B-Reasoning-2512",
            "model_type": "ministral3",
            "function_calling": True,
            # NOTE: Changed from "native" to "react" - mistral_common tekken tokenizer
            # produces corrupted output with Mistral3ForConditionalGeneration (vision model)
            "tool_calling_mode": "react",
            # Disable template thinking blocks to keep streaming responsive
            # The reasoning model still does step-by-step internally, but we skip
            # injecting enable_thinking so the template yields a direct answer.
            "supports_thinking": False,
            "thinking_tag_format": "brackets",  # [THINK]...[/THINK] vs angle <think>...</think>
            "rag_capable": True,
            "vision_capable": True,  # Ministral 3 has vision capabilities
            "code_capable": True,
            "context_length": 262144,  # 256K context window
            "vram_2bit_gb": 5,
            "vram_4bit_gb": 10,
            "vram_8bit_gb": 24,  # BF16 requires 24GB, quantization recommended
            "description": "Ministral 3 8B Reasoning with [THINK] blocks for step-by-step reasoning",
            # NOTE: GGUF disabled - llama-cpp-python 0.3.16 doesn't support mistral3 architecture yet
            # Official GGUF exists at mistralai/Ministral-3-8B-Reasoning-2512-GGUF (5.2GB Q4_K_M)
            # Re-enable when llama-cpp-python adds mistral3 support
            # "gguf_repo_id": "mistralai/Ministral-3-8B-Reasoning-2512-GGUF",
            # "gguf_filename": "Ministral-3-8B-Reasoning-2512-Q4_K_M.gguf",
        },
        # NOTE: Meta Llama - No 8B model comparable to Qwen3/Ministral3
        # Llama 3.3 is 70B only (42.5GB Q4_K_M GGUF - too large for most users)
        # Llama 3.1 8B is outdated. Meta does NOT have a "thinking" model.
        # CodeLlama is outdated - Qwen3-Coder is the better choice for code.
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
            "native_context_length": 131072,
            "yarn_max_context_length": 131072,
            "supports_yarn": False,
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
            "supports_thinking": True,  # Qwen3 supports both modes via enable_thinking flag
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 32768,  # 32K native, 131K with YaRN
            "native_context_length": 32768,
            "yarn_max_context_length": 131072,
            "supports_yarn": True,
            "vram_2bit_gb": 5,
            "vram_4bit_gb": 8,
            "vram_8bit_gb": 16,
            "description": "Qwen3 8B - supports both thinking (<think>) and instruct modes via enable_thinking flag",
            # GGUF variant (official Qwen GGUF)
            "gguf_repo_id": "Qwen/Qwen3-8B-GGUF",
            "gguf_filename": "Qwen3-8B-Q4_K_M.gguf",
            "local_storage_subdir": "Qwen",
            "aliases": [
                "Qwen 3 8B",
                "Qwen3 8B",
                "Qwen3-8B-Q4_K_M.gguf",
            ],
        },
        "qwen3.5-9b": {
            "name": "Qwen3.5-9B",
            "repo_id": "Qwen/Qwen3.5-9B",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": True,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 262144,
            "native_context_length": 262144,
            "yarn_max_context_length": 262144,
            "supports_yarn": False,
            "vram_2bit_gb": 6,
            "vram_4bit_gb": 10,
            "vram_8bit_gb": 12,
            "description": "Qwen3.5 9B long-context local GGUF model for conversation and analysis",
            "gguf_repo_id": "unsloth/Qwen3.5-9B-GGUF",
            "gguf_filename": "Qwen3.5-9B-Q8_0.gguf",
            "local_storage_subdir": "Qwen",
            "aliases": [
                "Qwen 3.5 9B",
                "Qwen3.5 9B",
                "Qwen3.5-9B-Q8_0.gguf",
            ],
        },
        "gpt-oss-20b": {
            "name": "GPT-OSS 20B",
            "repo_id": "openai/gpt-oss-20b",
            "model_type": "llm",
            "function_calling": False,
            "tool_calling_mode": "react",
            "supports_thinking": False,
            "supports_reasoning_effort": True,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 131072,
            "native_context_length": 4096,
            "yarn_max_context_length": 131072,
            "supports_yarn": True,
            "vram_2bit_gb": 10,
            "vram_4bit_gb": 14,
            "vram_8bit_gb": 20,
            "description": "GPT-OSS 20B GGUF for local llama.cpp code and reasoning workloads",
            "gguf_repo_id": "unsloth/gpt-oss-20b-GGUF",
            "gguf_filename": "gpt-oss-20b-F16.gguf",
            "gguf_default_n_ctx": 4096,
            "local_storage_subdir": "gpt_oss",
            "aliases": [
                "GPT-OSS",
                "GPT OSS",
                "gpt_oss",
                "gpt-oss-20b-F16.gguf",
            ],
        },
        "qwen3-14b": {
            "name": "Qwen3-14B",
            "repo_id": "Qwen/Qwen3-14B",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": True,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 131072,  # 128K with YaRN
            "native_context_length": 131072,
            "yarn_max_context_length": 131072,
            "supports_yarn": False,
            "vram_2bit_gb": 8,
            "vram_4bit_gb": 12,
            "vram_8bit_gb": 28,
            "description": "Qwen3 14B dense model with extended context and reasoning",
            "gguf_repo_id": "Qwen/Qwen3-14B-GGUF",
            "gguf_filename": "Qwen3-14B-Q4_K_M.gguf",
        },
        "qwen3-32b": {
            "name": "Qwen3-32B",
            "repo_id": "Qwen/Qwen3-32B",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": True,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 131072,  # 128K with YaRN
            "native_context_length": 131072,
            "yarn_max_context_length": 131072,
            "supports_yarn": False,
            "vram_2bit_gb": 14,
            "vram_4bit_gb": 24,
            "vram_8bit_gb": 64,
            "description": "Qwen3 32B dense model - best reasoning for high-VRAM systems",
            "gguf_repo_id": "Qwen/Qwen3-32B-GGUF",
            "gguf_filename": "Qwen3-32B-Q4_K_M.gguf",
        },
        "qwen3-30b-a3b": {
            "name": "Qwen3-30B-A3B (MoE)",
            "repo_id": "Qwen/Qwen3-30B-A3B",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": True,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 131072,  # 128K context
            "native_context_length": 131072,
            "yarn_max_context_length": 131072,
            "supports_yarn": False,
            "vram_2bit_gb": 10,
            "vram_4bit_gb": 19,
            "vram_8bit_gb": 38,
            "description": "Qwen3 30B MoE (3.3B active) - efficient 8B-like performance at 30B quality",
            "gguf_repo_id": "unsloth/Qwen3-30B-A3B-Instruct-GGUF",
            "gguf_filename": "Qwen3-30B-A3B-Instruct-Q4_K_M.gguf",
        },
        # Code-specialized models
        "qwen2.5-coder-7b": {
            "name": "Qwen2.5-Coder-7B-Instruct",
            "repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,  # Primary purpose
            "context_length": 131072,  # 128K native
            "vram_2bit_gb": 4,
            "vram_4bit_gb": 8,
            "vram_8bit_gb": 16,
            "description": "Qwen2.5 Coder 7B - excellent code generation for 8GB+ VRAM",
            # Official Qwen GGUF (4.68GB Q4_K_M)
            "gguf_repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
            "gguf_filename": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        },
        "qwen3-coder-30b-a3b": {
            "name": "Qwen3-Coder-30B-A3B-Instruct",
            "repo_id": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": False,  # Qwen3-Coder does NOT support thinking mode
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 262144,  # 256K native, 1M with Yarn
            "vram_2bit_gb": 11,
            "vram_4bit_gb": 15,  # Q3_K_M GGUF is 14.7GB file size
            "vram_8bit_gb": 33,
            "description": "Qwen3 Coder 30B MoE (3.3B active) - SOTA agentic coding with 256K context",
            # Using Q3_K_M (14.7GB) to fit in 16GB VRAM with room for KV cache
            "gguf_repo_id": "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF",
            "gguf_filename": "Qwen3-Coder-30B-A3B-Instruct-Q3_K_M.gguf",
        },
        # NOTE: Meta Llama 4 Maverick removed - GGUF is 243GB split across 5 files (impractical)
        # The model has 401B parameters (128 experts) and no single-file GGUF exists
        # NOTE: CodeLlama removed - outdated, Qwen2.5-Coder is significantly better
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
        "qwen3",
        "qwen3:8b",
        "qwen3:14b",
        "qwen3:30b-a3b",
        "qwen3:32b",
        "qwen3-coder:30b-a3b",
        "codellama",
        "custom",
    ]

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        """Normalize an identifier for loose alias comparisons."""
        return "".join(
            character
            for character in str(identifier or "").lower()
            if character.isalnum()
        )

    @classmethod
    def _iter_model_aliases(
        cls,
        model_info: Dict[str, Any],
    ) -> List[str]:
        """Return configured aliases for one local model."""
        aliases = list(model_info.get("aliases", []))
        for key in ("name", "gguf_filename"):
            value = model_info.get(key)
            if value:
                aliases.append(str(value))
        return aliases

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
            return [
                model_id
                for model_id in cls._SUPPORTED_LOCAL_MODEL_IDS
                if model_id in cls.LOCAL_MODELS
            ]
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
    def get_model_id_for_name(cls, provider: str, model_name: str) -> str:
        """Return the local model identifier for a display name or alias."""
        target = cls._normalize_identifier(model_name)
        if provider != "local" or not target:
            return ""

        for model_id, model_info in cls.LOCAL_MODELS.items():
            for alias in cls._iter_model_aliases(model_info):
                if cls._normalize_identifier(alias) == target:
                    return model_id
        return ""

    @classmethod
    def resolve_model_id(cls, provider: str, identifier: str) -> str:
        """Resolve a local model identifier from model_id, alias, or repo_id."""
        if provider != "local" or not identifier:
            return ""

        normalized = cls._normalize_identifier(identifier)
        for model_id in cls.LOCAL_MODELS:
            if cls._normalize_identifier(model_id) == normalized:
                return model_id

        model_id = cls.get_model_id_for_name(provider, identifier)
        if model_id:
            return model_id

        return cls.get_model_id_for_repo_id(provider, identifier)

    @classmethod
    def get_model_id_for_repo_id(cls, provider: str, repo_id: str) -> str:
        """Return the local model identifier for a base or GGUF repo ID."""
        if provider != "local" or not repo_id:
            return ""

        target = str(repo_id).strip().lower()

        for model_id, model_info in cls.LOCAL_MODELS.items():
            candidates = {
                str(model_info.get("repo_id", "")).lower(),
                str(model_info.get("gguf_repo_id", "")).lower(),
            }
            if target in candidates:
                return model_id
        return ""

    @classmethod
    def resolve_download_target(
        cls,
        provider: str,
        model_id: Optional[str] = None,
        repo_id: Optional[str] = None,
        prefer_pre_quantized: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Resolve the preferred downloadable artifact for a local model.

        For local LLMs, AIRunner now prefers vendor-provided GGUF artifacts
        whenever one is configured. This avoids downloading the full
        transformer checkpoint and then quantizing it locally.
        """
        if provider != "local":
            return None

        resolved_model_id = model_id or cls.get_model_id_for_repo_id(
            provider,
            repo_id or "",
        )
        if not resolved_model_id:
            return None

        model_info = cls.get_model_info(provider, resolved_model_id)
        if not model_info:
            return None

        if prefer_pre_quantized:
            gguf_info = cls.get_gguf_info(provider, resolved_model_id)
            if gguf_info:
                return {
                    "model_id": resolved_model_id,
                    "model_name": model_info.get("name", resolved_model_id),
                    "repo_id": gguf_info["repo_id"],
                    "model_type": "gguf",
                    "gguf_filename": gguf_info["filename"],
                    "quantization_bits": 0,
                }

        return {
            "model_id": resolved_model_id,
            "model_name": model_info.get("name", resolved_model_id),
            "repo_id": model_info.get("repo_id", repo_id or ""),
            "model_type": model_info.get("model_type", "llm"),
            "gguf_filename": None,
            "quantization_bits": None,
        }

    @staticmethod
    def _get_repo_owner(repo_id: str) -> str:
        """Extract the repository owner or organization from a repo ID."""
        if not repo_id:
            return ""
        return str(repo_id).split("/", 1)[0].strip()

    @classmethod
    def get_local_storage_path(
        cls,
        base_path: str,
        provider: str,
        model_id: Optional[str] = None,
        repo_id: Optional[str] = None,
        prefer_pre_quantized: bool = True,
    ) -> str:
        """Return the local directory used to store a model's files.

        GGUF downloads are single-file artifacts, so they are grouped by repo
        owner instead of by model name.
        """
        base_dir = os.path.join(
            os.path.expanduser(base_path),
            "text/models/llm/causallm",
        )
        resolved = cls.resolve_download_target(
            provider,
            model_id=model_id,
            repo_id=repo_id,
            prefer_pre_quantized=prefer_pre_quantized,
        )
        if not resolved:
            fallback = str(model_id or repo_id or "model")
            return os.path.join(base_dir, fallback.split("/")[-1] or "model")

        if resolved.get("model_type") == "gguf":
            resolved_model_id = str(resolved.get("model_id", ""))
            model_info = cls.get_model_info(provider, resolved_model_id)
            storage_subdir = str(
                model_info.get("local_storage_subdir", "")
            ).strip()
            if storage_subdir:
                return os.path.join(base_dir, storage_subdir)

            repo_owner = cls._get_repo_owner(resolved.get("repo_id", ""))
            if repo_owner:
                return os.path.join(base_dir, repo_owner)

        return os.path.join(
            base_dir,
            resolved.get("model_name", model_id or "model"),
        )

    @classmethod
    def get_expected_local_artifact_path(
        cls,
        base_path: str,
        provider: str,
        model_id: Optional[str] = None,
        repo_id: Optional[str] = None,
        prefer_pre_quantized: bool = True,
    ) -> str:
        """Return the exact local file or directory representing a model."""
        storage_path = cls.get_local_storage_path(
            base_path,
            provider,
            model_id=model_id,
            repo_id=repo_id,
            prefer_pre_quantized=prefer_pre_quantized,
        )
        resolved = cls.resolve_download_target(
            provider,
            model_id=model_id,
            repo_id=repo_id,
            prefer_pre_quantized=prefer_pre_quantized,
        )
        if resolved and resolved.get("model_type") == "gguf":
            gguf_filename = resolved.get("gguf_filename")
            if gguf_filename:
                return os.path.join(storage_path, gguf_filename)
        return storage_path

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
