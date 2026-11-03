"""Runtime probing for the local-inference capability payload.

Split from ``local_capability`` so health probing and the
loaded-model proof stay a single concern. A model counts as
loaded only when a READY health report names the served model
in its metadata (``model_id``, or a ``model_path`` whose file
name resolves to a known model). READY with no such metadata
proves the runtime is up, not which model it serves, so no
model is reported loaded; a configured selection is never proof.
"""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Dict, Mapping, Optional, Tuple

from airunner_services.llm.local_capability_models import (
    LOCAL_PROVIDER,
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


def probe_local_health(
    registry: Optional[RuntimeRegistry],
) -> Tuple[Optional[RuntimeHealth], bool]:
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


def _capability_runtime_metadata(metadata: Mapping[str, Any]) -> Dict[str, Any]:
    """Expose backend selection fields without leaking local filesystem paths."""
    keys = (
        "backend_profile",
        "backend_artifact_id",
        "backend_manifest_sha256",
        "backend_profile_verified",
        "requested_device",
        "actual_device",
        "offloaded_layers",
        "fit",
        "backend_unavailable",
        "backend_selection_deferred",
    )
    selected = {key: metadata[key] for key in keys if key in metadata}
    executable = metadata.get("backend_executable")
    if isinstance(executable, str) and executable.strip():
        name = PureWindowsPath(PurePosixPath(executable).name).name
        if name:
            selected["backend_binary"] = name
    return selected


def runtime_entry(
    health: Optional[RuntimeHealth], *, failed: bool
) -> Dict[str, Any]:
    """Return live local-runtime health, or an honest marker."""
    if health is None and failed:
        return {
            "status": "failed",
            "details": "healthcheck failed",
            "descriptor": None,
            "metadata": {},
        }
    if health is None:
        return {
            "status": "unavailable",
            "details": "",
            "descriptor": None,
            "metadata": {},
        }
    return {
        "status": health.status.value,
        "details": health.details,
        "descriptor": _descriptor_entry(health),
        "metadata": _capability_runtime_metadata(health.metadata),
    }


def _served_model_id(metadata: Mapping[str, Any]) -> str:
    """Resolve the served model named by health metadata, or ""."""
    served = metadata.get("model_id")
    if isinstance(served, str) and served.strip():
        resolved = LLMProviderConfig.resolve_model_id(LOCAL_PROVIDER, served)
        if resolved:
            return resolved
    model_path = metadata.get("model_path")
    if isinstance(model_path, str) and model_path.strip():
        name = PureWindowsPath(PurePosixPath(model_path).name).name
        return LLMProviderConfig.resolve_model_id(LOCAL_PROVIDER, name)
    return ""


def _proven_loaded_id(health: Optional[RuntimeHealth]) -> str:
    """Return the model id READY health metadata proves loaded.

    READY alone proves only that the runtime answers; without
    metadata naming the served model the loaded id is unknown
    and reported as "" (no model ``loaded``), never as the
    configured selection.
    """
    if health is None or health.status is not RuntimeHealthStatus.READY:
        return ""
    return _served_model_id(health.metadata)


def proven_loaded_model_id(
    registry: Optional[RuntimeRegistry] = None,
    configured_model_id: str = "",
) -> str:
    """Return the READY-proven loaded model id, or "".

    ``configured_model_id`` is accepted for caller compatibility
    and is never used as proof of a load.
    """
    del configured_model_id
    health, _failed = probe_local_health(registry)
    return _proven_loaded_id(health)


__all__ = [
    "probe_local_health",
    "proven_loaded_model_id",
    "runtime_entry",
]
