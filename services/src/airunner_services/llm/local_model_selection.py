"""Documented default selection for local GGUF models.

When no local model is configured, the effective selection is
``DEFAULT_LOCAL_MODEL_ID``: the first supported GGUF model, with
the lowest 4-bit VRAM need of the supported candidates and
function calling, so a fresh install has a truthful, loadable
selection instead of an empty one. The default is a configured
selection only: it never implies the model is loaded, which is
proven separately by the local-capability runtime probe, and it
does not download or load anything by itself.
"""

from __future__ import annotations

from airunner_services.llm.provider_config import LLMProviderConfig

LOCAL_PROVIDER = "local"
DEFAULT_LOCAL_MODEL_ID = "qwen3.5-9b"


def _is_gguf_candidate(model_id: str) -> bool:
    """Return whether a supported model ships a GGUF download."""
    info = LLMProviderConfig.get_gguf_info(LOCAL_PROVIDER, model_id)
    return info is not None


def default_local_model_id() -> str:
    """Return the documented default local model id, or ""."""
    supported = LLMProviderConfig.get_models_for_provider(LOCAL_PROVIDER)
    if DEFAULT_LOCAL_MODEL_ID in supported and _is_gguf_candidate(
        DEFAULT_LOCAL_MODEL_ID
    ):
        return DEFAULT_LOCAL_MODEL_ID
    for model_id in supported:
        if _is_gguf_candidate(model_id):
            return model_id
    return ""


def effective_local_model_id(configured_model_id: str = "") -> str:
    """Return the explicit selection, else the documented default."""
    if configured_model_id:
        resolved = LLMProviderConfig.resolve_model_id(
            LOCAL_PROVIDER, configured_model_id
        )
        if resolved:
            return resolved
    return default_local_model_id()


__all__ = [
    "DEFAULT_LOCAL_MODEL_ID",
    "default_local_model_id",
    "effective_local_model_id",
]
