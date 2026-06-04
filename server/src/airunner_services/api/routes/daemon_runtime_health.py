"""Runtime health and metadata helpers for daemon route endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from airunner_services.contract_enums import ModelStatus
from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import RuntimeHealthStatus, RuntimeKind

ART_MODEL_NAME = "SD"


def loaded_model_names(request: Request) -> set[str]:
    """Return the lifecycle service's loaded model names when available."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    if lifecycle_service is None:
        return set()
    status = lifecycle_service.get_status()
    return set(status.get("loaded_models") or [])


def runtime_loaded(request: Request, runtime: RuntimeKind) -> bool:
    """Return whether the runtime is reported as loaded."""
    loaded_models = loaded_model_names(request)
    model_name = ART_MODEL_NAME
    if runtime is not RuntimeKind.ART:
        model_name = runtime.value.upper()
    return model_name in loaded_models


def local_llm_worker_status(request: Request) -> Any:
    """Return the lifecycle-owned local LLM status when available."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    status_getter = getattr(
        lifecycle_service, "current_llm_model_status", None
    )
    if not callable(status_getter):
        return None
    return status_getter()


def configured_llm_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Merge persisted LLM model identity into runtime metadata."""
    merged = dict(metadata)
    settings = None
    try:
        settings = LLMGeneratorSettings.objects.first()
    except Exception:
        settings = None
    if settings is None:
        return merged
    for key in ("model_path", "model_id", "model_version"):
        value = str(getattr(settings, key, "") or "").strip()
        if value and key not in merged:
            merged[key] = value
    return merged


def prefer_local_llm_worker_status(
    request: Request,
    client: RuntimeClient,
    status: str,
    details: str,
    metadata: dict[str, Any],
) -> tuple[str, str, dict[str, Any], bool]:
    """Prefer the daemon's live local LLM worker status when available."""
    if client.descriptor.runtime is not RuntimeKind.LLM:
        return status, details, metadata, False
    worker_status = local_llm_worker_status(request)
    override = {
        ModelStatus.LOADING: (
            RuntimeHealthStatus.STARTING.value,
            "loading",
        ),
        ModelStatus.LOADED: (RuntimeHealthStatus.READY.value, "loaded"),
        ModelStatus.READY: (RuntimeHealthStatus.READY.value, "loaded"),
        ModelStatus.FAILED: (RuntimeHealthStatus.FAILED.value, "failed"),
        ModelStatus.UNLOADED: (
            RuntimeHealthStatus.STOPPED.value,
            "unloaded",
        ),
    }.get(worker_status)
    if override is None:
        return status, details, metadata, False
    merged_metadata = configured_llm_metadata(metadata)
    merged_metadata["model_status"] = override[1]
    return override[0], override[1], merged_metadata, True


def health_fields(
    request: Request,
    client: RuntimeClient,
    loaded: bool,
) -> tuple[str, str, dict[str, Any]]:
    """Normalize runtime health values for the daemon status payload."""
    health = client.healthcheck()
    status = health.status.value
    details = health.details
    metadata = dict(health.metadata)
    status, details, metadata, local_override_applied = (
        prefer_local_llm_worker_status(
            request, client, status, details, metadata
        )
    )
    if health.status is RuntimeHealthStatus.UNKNOWN and (
        not local_override_applied
    ):
        if loaded:
            status = RuntimeHealthStatus.READY.value
            details = details or "loaded"
            metadata.setdefault("model_status", "loaded")
        else:
            status = RuntimeHealthStatus.STOPPED.value
            details = details or "not loaded"
    return status, details, metadata


def supports_cancellation(client: RuntimeClient) -> bool:
    """Return whether the runtime client overrides cancellation support."""
    return type(client).cancel is not RuntimeClient.cancel


def infer_loaded_state(
    status: str,
    metadata: dict[str, Any],
    lifecycle_loaded: bool,
) -> bool:
    """Infer the loaded flag from runtime health before lifecycle state."""
    model_status = str(metadata.get("model_status", "")).strip().lower()
    if model_status in {"loaded", "ready", "loading"}:
        return True
    if model_status in {"unloaded", "failed"}:
        return False
    ready_values = {
        RuntimeHealthStatus.READY.value,
        RuntimeHealthStatus.STARTING.value,
    }
    failed_values = {
        RuntimeHealthStatus.STOPPED.value,
        RuntimeHealthStatus.FAILED.value,
    }
    if status in ready_values:
        return True
    if status in failed_values:
        return False
    return lifecycle_loaded
