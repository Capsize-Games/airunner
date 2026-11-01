"""Machine-readable local-inference capability contract.

Another local process (e.g. the UwUChat Local Node) queries this
payload to learn which GGUF models this daemon can run locally,
their context and VRAM needs, which companion pipelines stay
local, and whether the local LLM runtime is currently ready —
without loading a model or guessing from prose docs.

The builder never raises for a missing runtime: reporting
``unavailable`` is the point, so a consumer can decide to wait,
load a model, or stay offline instead of falling back to cloud.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from airunner_services.llm.companion.local_routing import (
    PIPELINE_ROUTES,
    REMOTE_PROVIDER_OPENROUTER,
)
from airunner_services.llm.provider_config import LLMProviderConfig
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
)
from airunner_services.runtimes.registry import (
    DEFAULT_PROVIDER,
    RuntimeRegistry,
)

CAPABILITY_CONTRACT = "airunner.local-inference"
CAPABILITY_VERSION = "1"
LOCAL_PROVIDER = "local"
_INFERENCE_ENDPOINTS: Dict[str, str] = {
    "generate": "/api/v1/llm/generate",
    "stream": "/api/v1/llm/stream",
    "models": "/api/v1/llm/models",
    "load": "/api/v1/llm/load",
    "unload": "/api/v1/llm/unload",
    "capability": "/api/v1/llm/local-inference",
}


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


def _pipeline_entries() -> List[Dict[str, Any]]:
    """Return the local-first routing matrix, pipeline by name."""
    entries = []
    for pipeline, route in sorted(
        PIPELINE_ROUTES.items(), key=lambda item: item[0].value
    ):
        entries.append(
            {
                "pipeline": pipeline.value,
                "runtime": (route.runtime.value if route.runtime else None),
                "provider": route.provider,
                "local_only": route.runtime is None,
            }
        )
    return entries


def _resolve_local_client(
    registry: Optional[RuntimeRegistry],
) -> Optional[RuntimeClient]:
    """Resolve the local LLM client under either known provider."""
    if registry is None:
        return None
    for provider in (LOCAL_PROVIDER, DEFAULT_PROVIDER):
        try:
            return registry.resolve(RuntimeKind.LLM, provider)
        except KeyError:
            continue
    return None


def _probe_local_health(
    registry: Optional[RuntimeRegistry],
) -> tuple[Optional[RuntimeHealth], bool]:
    """Probe local health once; second value flags a failure."""
    client = _resolve_local_client(registry)
    if client is None:
        return None, False
    try:
        return client.healthcheck(), False
    except Exception:
        return None, True


def _descriptor_entry(health: RuntimeHealth) -> Dict[str, Any]:
    """Return the wire form of a runtime descriptor."""
    descriptor = health.descriptor
    return {
        "runtime": descriptor.runtime.value,
        "provider": descriptor.provider,
        "mode": descriptor.mode.value,
        "transport": descriptor.transport.value,
        "supports_streaming": descriptor.supports_streaming,
        "allows_model_control": descriptor.allows_model_control,
    }


def _runtime_entry(
    health: Optional[RuntimeHealth], *, failed: bool
) -> Dict[str, Any]:
    """Return live local-runtime health, or an honest marker."""
    if health is None and failed:
        return {
            "status": "failed",
            "details": "healthcheck failed",
            "descriptor": None,
        }
    if health is None:
        return {"status": "unavailable", "details": "", "descriptor": None}
    return {
        "status": health.status.value,
        "details": health.details,
        "descriptor": _descriptor_entry(health),
    }


def _proven_loaded_id(
    health: Optional[RuntimeHealth], configured_id: str
) -> str:
    """Return the model id the runtime proves is loaded, or "".

    READY is the proof: the sidecar reports it only when its
    process answers ``/health`` and the local fallback only
    when the model last reported LOADED/READY. A configured
    selection alone never proves a load. When health metadata
    names the served model it wins; otherwise a READY local
    runtime can only be serving the configured model.
    """
    if health is None or health.status is not RuntimeHealthStatus.READY:
        return ""
    served = health.metadata.get("model_id")
    if isinstance(served, str) and served.strip():
        return LLMProviderConfig.resolve_model_id(LOCAL_PROVIDER, served)
    return configured_id


def proven_loaded_model_id(
    registry: Optional[RuntimeRegistry] = None,
    configured_model_id: str = "",
) -> str:
    """Return the READY-proven loaded model id, or ""."""
    health, _failed = _probe_local_health(registry)
    return _proven_loaded_id(health, configured_model_id)


def _routing_entry() -> Dict[str, Any]:
    """Return default-local versus consent-gated remote routing."""
    return {
        "default_provider": DEFAULT_PROVIDER,
        "remote_provider": REMOTE_PROVIDER_OPENROUTER,
        "remote_requires_consent": True,
    }


def _model_entries(configured_id: str, loaded_id: str) -> List[Dict[str, Any]]:
    """Return every supported local model's capability entry."""
    model_ids = LLMProviderConfig.get_models_for_provider(LOCAL_PROVIDER)
    return [_model_entry(m, configured_id, loaded_id) for m in model_ids]


def build_local_capability(
    registry: Optional[RuntimeRegistry] = None,
    configured_model_id: str = "",
) -> Dict[str, Any]:
    """Build the capability payload (never raises if down)."""
    health, failed = _probe_local_health(registry)
    loaded_id = _proven_loaded_id(health, configured_model_id)
    return {
        "contract": CAPABILITY_CONTRACT,
        "contract_version": CAPABILITY_VERSION,
        "provider": LOCAL_PROVIDER,
        "models": _model_entries(configured_model_id, loaded_id),
        "pipelines": _pipeline_entries(),
        "runtime": _runtime_entry(health, failed=failed),
        "routing": _routing_entry(),
        "endpoints": dict(_INFERENCE_ENDPOINTS),
    }


__all__ = [
    "CAPABILITY_CONTRACT",
    "CAPABILITY_VERSION",
    "LOCAL_PROVIDER",
    "build_local_capability",
    "proven_loaded_model_id",
]
