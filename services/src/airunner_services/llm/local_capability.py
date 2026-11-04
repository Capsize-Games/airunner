"""Machine-readable local-inference capability contract.

Another local process (e.g. the UwUChat Local Node) queries this
payload to learn which GGUF models this daemon can run locally,
their context and VRAM needs, which companion pipelines stay
local, and whether the local LLM runtime is currently ready —
without loading a model or guessing from prose docs.

The builder never raises for a missing runtime: reporting
``unavailable`` is the point, so a consumer can decide to wait,
load a model, or stay offline instead of falling back to cloud.

Model entries live in ``local_capability_models`` and runtime
probing (including the loaded-model proof) in
``local_capability_runtime``; this module keeps the contract
constants, routing, and payload assembly, and re-exports the
public names so existing imports keep working.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from airunner_services.runtimes.local_pipeline import (
    LOCAL_PIPELINE_ROUTES,
    REMOTE_PROVIDER_OPENROUTER,
)
from airunner_services.llm.local_capability_models import (
    LOCAL_PROVIDER,
    model_entries,
)
from airunner_services.llm.local_capability_runtime import (
    _proven_loaded_id,
    probe_local_health,
    proven_loaded_model_id,
    runtime_entry,
)
from airunner_services.runtimes.registry import (
    DEFAULT_PROVIDER,
    RuntimeRegistry,
)

CAPABILITY_CONTRACT = "airunner.local-inference"
CAPABILITY_VERSION = "1"
_INFERENCE_ENDPOINTS: Dict[str, str] = {
    "generate": "/api/v1/llm/generate",
    "stream": "/api/v1/llm/stream",
    "models": "/api/v1/llm/models",
    "load": "/api/v1/llm/load",
    "unload": "/api/v1/llm/unload",
    "capability": "/api/v1/llm/local-inference",
}


def _pipeline_entries() -> List[Dict[str, Any]]:
    """Return the local-first routing matrix, pipeline by name."""
    entries = []
    for pipeline, route in sorted(
        LOCAL_PIPELINE_ROUTES.items(), key=lambda item: item[0].value
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


def _routing_entry() -> Dict[str, Any]:
    """Return default-local versus consent-gated remote routing."""
    return {
        "default_provider": DEFAULT_PROVIDER,
        "remote_provider": REMOTE_PROVIDER_OPENROUTER,
        "remote_requires_consent": True,
    }


def build_local_capability(
    registry: Optional[RuntimeRegistry] = None,
    configured_model_id: str = "",
) -> Dict[str, Any]:
    """Build the capability payload (never raises if down)."""
    health, failed = probe_local_health(registry)
    loaded_id = _proven_loaded_id(health)
    return {
        "contract": CAPABILITY_CONTRACT,
        "contract_version": CAPABILITY_VERSION,
        "provider": LOCAL_PROVIDER,
        "models": model_entries(configured_model_id, loaded_id),
        "pipelines": _pipeline_entries(),
        "runtime": runtime_entry(health, failed=failed),
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
