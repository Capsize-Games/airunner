"""Local model entries for the local-inference capability payload.

Split from ``local_capability`` so model-catalog shaping stays a
single concern: GGUF identity, runtime profiles, VRAM needs, and
the configured-versus-loaded flags for each supported local model.
``loaded`` is only ever the READY-proven id passed in by the
runtime probe; this module never infers a load from configuration.
"""

from __future__ import annotations

from typing import Any, Dict, List

from airunner_services.llm.provider_config import LLMProviderConfig

LOCAL_PROVIDER = "local"


def _gguf_entry(model_id: str) -> Dict[str, Any]:
    """Return the GGUF download identity for one local model."""
    info = LLMProviderConfig.get_gguf_info(LOCAL_PROVIDER, model_id)
    return {
        "supported": info is not None,
        "repo_id": info["repo_id"] if info else None,
        "filename": info["filename"] if info else None,
    }


def _profile_entries(model_id: str) -> List[Dict[str, Any]]:
    """Return named GGUF runtime profiles (name plus n_ctx)."""
    info = LLMProviderConfig.get_model_info(LOCAL_PROVIDER, model_id)
    profiles = info.get("gguf_runtime_profiles") or {}
    entries = [
        {"name": name, "n_ctx": profile.get("n_ctx")}
        for name, profile in sorted(profiles.items())
    ]
    if entries:
        return entries
    legacy = LLMProviderConfig.get_gguf_runtime_profile(
        LOCAL_PROVIDER, model_id
    )
    if legacy:
        return [{"name": "default", "n_ctx": legacy.get("n_ctx")}]
    return []


def _vram_entry(info: Dict[str, Any]) -> Dict[str, int]:
    """Return per-quantization VRAM needs in GB."""
    return {
        "2bit": int(info.get("vram_2bit_gb", 0) or 0),
        "4bit": int(info.get("vram_4bit_gb", 0) or 0),
        "8bit": int(info.get("vram_8bit_gb", 0) or 0),
    }


def _model_entry(
    model_id: str, configured_id: str, loaded_id: str
) -> Dict[str, Any]:
    """Return one local model entry (configured != loaded)."""
    info = LLMProviderConfig.get_model_info(LOCAL_PROVIDER, model_id)
    return {
        "id": model_id,
        "name": str(info.get("name", model_id)),
        "configured": bool(configured_id) and model_id == configured_id,
        "loaded": bool(loaded_id) and model_id == loaded_id,
        "context_length": int(info.get("context_length", 0) or 0),
        "function_calling": bool(info.get("function_calling")),
        "tool_calling_mode": str(info.get("tool_calling_mode", "")),
        "supports_thinking": bool(info.get("supports_thinking")),
        "vram_gb": _vram_entry(info),
        "gguf": _gguf_entry(model_id),
        "gguf_runtime_profiles": _profile_entries(model_id),
    }


def model_entries(configured_id: str, loaded_id: str) -> List[Dict[str, Any]]:
    """Return every supported local model's capability entry."""
    model_ids = LLMProviderConfig.get_models_for_provider(LOCAL_PROVIDER)
    return [_model_entry(m, configured_id, loaded_id) for m in model_ids]


__all__ = ["LOCAL_PROVIDER", "model_entries"]
