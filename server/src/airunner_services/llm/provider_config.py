"""Model-owned configuration for LLM providers and local model metadata."""

import os
from typing import Any, Dict, List, Optional


class LLMProviderConfig:
    """Available models for each LLM provider."""

    _SUPPORTED_LOCAL_MODEL_IDS = (
        "qwen3.5-9b",
        "gpt-oss-20b",
        "custom",
    )

    LOCAL_MODELS = {
        "qwen2.5-7b": {
            "name": "Qwen2.5-7B-Instruct",
            "repo_id": "Qwen/Qwen2.5-7B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 131072,
            "native_context_length": 131072,
            "yarn_max_context_length": 131072,
            "supports_yarn": False,
            "vram_2bit_gb": 4,
            "vram_4bit_gb": 7,
            "vram_8bit_gb": 14,
            "description": "Qwen 2.5 7B with Hermes-style JSON tool calling",
            "gguf_repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
            "gguf_filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
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
            "gguf_runtime_profiles": {
                "default": {
                    "n_ctx": 32768,
                    "n_batch": 256,
                },
                "combined_tts": {
                    "n_ctx": 4096,
                    "n_gpu_layers": 10,
                    "n_batch": 256,
                },
            },
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
            "gguf_default_n_batch": 256,
            "local_storage_subdir": "gpt_oss",
            "aliases": [
                "GPT-OSS",
                "GPT OSS",
                "gpt_oss",
                "gpt-oss-20b-F16.gguf",
            ],
            "gguf_runtime_profiles": {
                "default": {
                    "n_ctx": 4096,
                    "n_batch": 256,
                },
                "combined_tts": {
                    "n_ctx": 4096,
                    "n_gpu_layers": 0,
                    "n_batch": 256,
                },
            },
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
            "context_length": 131072,
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
            "context_length": 131072,
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
            "context_length": 131072,
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
        "qwen2.5-coder-7b": {
            "name": "Qwen2.5-Coder-7B-Instruct",
            "repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 131072,
            "vram_2bit_gb": 4,
            "vram_4bit_gb": 8,
            "vram_8bit_gb": 16,
            "description": "Qwen2.5 Coder 7B - excellent code generation for 8GB+ VRAM",
            "gguf_repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
            "gguf_filename": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        },
        "qwen3-coder-30b-a3b": {
            "name": "Qwen3-Coder-30B-A3B-Instruct",
            "repo_id": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
            "model_type": "llm",
            "function_calling": True,
            "tool_calling_mode": "json",
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "context_length": 262144,
            "vram_2bit_gb": 11,
            "vram_4bit_gb": 15,
            "vram_8bit_gb": 33,
            "description": "Qwen3 Coder 30B MoE (3.3B active) - SOTA agentic coding with 256K context",
            "gguf_repo_id": "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF",
            "gguf_filename": "Qwen3-Coder-30B-A3B-Instruct-Q3_K_M.gguf",
        },
        "custom": {
            "name": "Custom Local Path",
            "repo_id": "",
            "model_type": "llm",
            "function_calling": False,
            "tool_calling_mode": "react",
            "supports_thinking": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": False,
            "context_length": 0,
            "vram_2bit_gb": 0,
            "vram_4bit_gb": 0,
            "vram_8bit_gb": 0,
            "description": "Use custom model path (auto-detects tool calling mode)",
        },
    }

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
        return "".join(
            character
            for character in str(identifier or "").lower()
            if character.isalnum()
        )

    @classmethod
    def _iter_model_aliases(cls, model_info: Dict[str, Any]) -> List[str]:
        aliases = list(model_info.get("aliases", []))
        for key in ("name", "gguf_filename"):
            value = model_info.get(key)
            if value:
                aliases.append(str(value))
        return aliases

    @staticmethod
    def get_gguf_runtime_profile(
        provider: str,
        model_id: str,
        profile_name: str = "default",
    ) -> Dict[str, Any]:
        """Return one GGUF runtime profile for one local model."""
        model_info = LLMProviderConfig.get_model_info(provider, model_id) or {}
        profiles = model_info.get("gguf_runtime_profiles") or {}
        profile = profiles.get(profile_name) or {}
        if profile:
            return dict(profile)

        legacy_profile: Dict[str, Any] = {}
        default_n_ctx = model_info.get("gguf_default_n_ctx")
        if default_n_ctx:
            legacy_profile["n_ctx"] = int(default_n_ctx)
        default_n_batch = model_info.get("gguf_default_n_batch")
        if default_n_batch:
            legacy_profile["n_batch"] = int(default_n_batch)
        return legacy_profile

    @classmethod
    def get_models_for_provider(cls, provider: str) -> List[str]:
        if provider == "local":
            return [
                model_id
                for model_id in cls._SUPPORTED_LOCAL_MODEL_IDS
                if model_id in cls.LOCAL_MODELS
            ]
        if provider == "openrouter":
            return cls.OPENROUTER_MODELS
        if provider == "ollama":
            return cls.OLLAMA_MODELS
        return []

    @classmethod
    def get_model_display_name(cls, provider: str, model_id: str) -> str:
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            if model_info["function_calling"]:
                return f"{model_info['name']} ⚡"
            return f"{model_info['name']}"
        return model_id

    @classmethod
    def get_model_info(cls, provider: str, model_id: str) -> Dict:
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            return cls.LOCAL_MODELS[model_id]
        return {}

    @classmethod
    def get_model_id_for_name(cls, provider: str, model_name: str) -> str:
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
        cls,
        provider: str,
        model_id: str,
        quantization_bits: int,
    ) -> int:
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            vram_key = f"vram_{quantization_bits}bit_gb"
            return model_info.get(vram_key, 0)
        return 0

    @classmethod
    def requires_download(cls, provider: str, model_id: str) -> bool:
        return provider == "local" and model_id != "custom"

    @classmethod
    def has_gguf_support(cls, provider: str, model_id: str) -> bool:
        if provider == "local" and model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            return bool(
                model_info.get("gguf_repo_id")
                and model_info.get("gguf_filename")
            )
        return False

    @classmethod
    def has_gguf_variant(cls, model_id: str) -> bool:
        if model_id in cls.LOCAL_MODELS:
            model_info = cls.LOCAL_MODELS[model_id]
            return bool(
                model_info.get("gguf_repo_id")
                and model_info.get("gguf_filename")
            )
        return False

    @classmethod
    def get_gguf_info(
        cls,
        provider: str,
        model_id: str,
    ) -> Optional[Dict[str, str]]:
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


__all__ = ["LLMProviderConfig"]
