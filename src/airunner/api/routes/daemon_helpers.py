"""Helper functions for daemon status and control routes."""

from __future__ import annotations

from typing import Any, List, Optional
from uuid import uuid4

from fastapi import HTTPException, Request

from airunner.api.models.runtime_route_request import RuntimeRouteRequest
from airunner.api.models.runtime_summary_response import RuntimeSummaryResponse
from airunner.ipc.messages import EnvelopeStatus, RequestEnvelope, ResponseEnvelope
from airunner.enums import ModelStatus
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import RuntimeAction, RuntimeHealthStatus, RuntimeKind

ART_MODEL_NAME = "SD"


def get_runtime_registry(request: Request) -> Any:
    """Return the runtime registry stored on FastAPI app state."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> Any:
    """Return the runtime registry or raise when daemon state is missing."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(
            status_code=503,
            detail="Runtime registry not available",
        )
    return runtime_registry


def parse_runtime_kind(runtime_name: str) -> RuntimeKind:
    """Parse a runtime path value into a known runtime kind."""
    try:
        return RuntimeKind(runtime_name.lower())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Runtime not found") from exc


def route_alias(route: Any) -> str:
    """Return a stable alias label for a registered runtime route."""
    return f"{route.provider}:{route.deployment_mode}"


def client_key(
    client: RuntimeClient,
) -> tuple[str, str, str, str, Optional[str]]:
    """Return a stable dedupe key for a runtime client descriptor."""
    descriptor = client.descriptor
    return (
        descriptor.runtime.value,
        descriptor.provider,
        descriptor.mode.value,
        descriptor.transport.value,
        descriptor.endpoint,
    )


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

    (
        status,
        details,
        metadata,
        local_override_applied,
    ) = _prefer_local_llm_worker_status(
        request,
        client,
        status,
        details,
        metadata,
    )

    if health.status is RuntimeHealthStatus.UNKNOWN and not local_override_applied:
        if loaded:
            status = RuntimeHealthStatus.READY.value
            details = details or "loaded"
            metadata.setdefault("model_status", "loaded")
        else:
            status = RuntimeHealthStatus.STOPPED.value
            details = details or "not loaded"

    return status, details, metadata


def _prefer_local_llm_worker_status(
    request: Request,
    client: RuntimeClient,
    status: str,
    details: str,
    metadata: dict[str, Any],
) -> tuple[str, str, dict[str, Any], bool]:
    """Prefer the daemon's live local LLM worker status when available."""
    if client.descriptor.runtime is not RuntimeKind.LLM:
        return status, details, metadata, False

    worker_status = _local_llm_worker_status(request)
    override = {
        ModelStatus.LOADING: (RuntimeHealthStatus.STARTING.value, "loading"),
        ModelStatus.LOADED: (RuntimeHealthStatus.READY.value, "loaded"),
        ModelStatus.READY: (RuntimeHealthStatus.READY.value, "loaded"),
        ModelStatus.FAILED: (RuntimeHealthStatus.FAILED.value, "failed"),
        ModelStatus.UNLOADED: (RuntimeHealthStatus.STOPPED.value, "unloaded"),
    }.get(worker_status)
    if override is None:
        return status, details, metadata, False

    merged_metadata = _configured_llm_metadata(metadata)
    merged_metadata["model_status"] = override[1]
    return override[0], override[1], merged_metadata, True


def _local_llm_worker_status(request: Request) -> Any:
    """Return the current daemon-local LLM worker status when one exists."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    worker_manager = getattr(lifecycle_service, "worker_manager", None)
    worker = getattr(worker_manager, "_llm_generate_worker", None)
    if worker is None:
        return None

    status_getter = getattr(worker, "current_model_status", None)
    if callable(status_getter):
        try:
            status = status_getter()
        except Exception:
            status = None
        if status is not None:
            return status

    model_manager = getattr(worker, "_model_manager", None)
    if model_manager is not None and getattr(model_manager, "_chat_model", None) is not None:
        return ModelStatus.LOADED
    return None


def _configured_llm_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Merge persisted LLM model identity into runtime metadata."""
    merged = dict(metadata)
    try:
        from airunner.components.llm.data.llm_generator_settings import (
            LLMGeneratorSettings,
        )

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


def supports_cancellation(client: RuntimeClient) -> bool:
    """Return whether the runtime client overrides cancellation support."""
    return type(client).cancel is not RuntimeClient.cancel


def build_runtime_summary(
    request: Request,
    client: RuntimeClient,
    route_aliases: List[str],
) -> RuntimeSummaryResponse:
    """Build a daemon-facing runtime summary for a client."""
    lifecycle_loaded = runtime_loaded(request, client.descriptor.runtime)
    status, details, metadata = health_fields(
        request,
        client,
        lifecycle_loaded,
    )
    loaded = infer_loaded_state(status, metadata, lifecycle_loaded)
    descriptor = client.descriptor
    return RuntimeSummaryResponse(
        runtime=descriptor.runtime.value,
        provider=descriptor.provider,
        mode=descriptor.mode.value,
        transport=descriptor.transport.value,
        status=status,
        loaded=loaded,
        details=details,
        supports_streaming=descriptor.supports_streaming,
        allows_model_control=descriptor.allows_model_control,
        supports_cancellation=supports_cancellation(client),
        metadata=metadata,
        route_aliases=route_aliases,
    )


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
    if status in {
        RuntimeHealthStatus.READY.value,
        RuntimeHealthStatus.STARTING.value,
    }:
        return True
    if status in {
        RuntimeHealthStatus.STOPPED.value,
        RuntimeHealthStatus.FAILED.value,
    }:
        return False
    return lifecycle_loaded


def collect_runtime_summaries(request: Request) -> List[RuntimeSummaryResponse]:
    """Collect deduplicated runtime summaries from the registry."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        return []

    grouped: dict[
        tuple[str, str, str, str, Optional[str]], dict[str, Any]
    ] = {}
    for route in runtime_registry.list_routes():
        client = runtime_registry.resolve(
            route.runtime,
            route.provider,
            route.deployment_mode,
        )
        key = client_key(client)
        entry = grouped.setdefault(
            key,
            {"client": client, "route_aliases": []},
        )
        alias = route_alias(route)
        if alias not in entry["route_aliases"]:
            entry["route_aliases"].append(alias)

    summaries = [
        build_runtime_summary(
            request,
            entry["client"],
            sorted(entry["route_aliases"]),
        )
        for entry in grouped.values()
    ]
    return sorted(summaries, key=lambda item: (item.runtime, item.provider))


def resolve_runtime_client(
    request: Request,
    runtime: RuntimeKind,
    provider: str,
    deployment_mode: str,
) -> RuntimeClient:
    """Resolve a runtime client or raise when no route is registered."""
    runtime_registry = require_runtime_registry(request)
    try:
        return runtime_registry.resolve(runtime, provider, deployment_mode)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Runtime route not found",
        ) from exc


def runtime_failure_status(response: ResponseEnvelope) -> int:
    """Map a runtime failure envelope to an HTTP status code."""
    error = response.error
    if error is None:
        return 502
    if error.code.endswith("_timeout"):
        return 504
    if error.code.endswith("_unsupported"):
        return 409
    return 502


def ensure_success(response: ResponseEnvelope) -> ResponseEnvelope:
    """Raise an HTTP error when a runtime control action fails."""
    if response.status is not EnvelopeStatus.FAILED:
        return response

    raise HTTPException(
        status_code=runtime_failure_status(response),
        detail=response.error.message if response.error else "Runtime action failed",
    )


def invoke_runtime_action(
    client: RuntimeClient,
    runtime: RuntimeKind,
    action: RuntimeAction,
    route_request: RuntimeRouteRequest,
) -> ResponseEnvelope:
    """Invoke a runtime lifecycle action through the neutral envelope."""
    response = client.invoke(
        RequestEnvelope(
            request_id=route_request.request_id or str(uuid4()),
            runtime=runtime,
            action=action,
            provider=route_request.provider,
            metadata=dict(route_request.metadata or {}),
        )
    )
    return ensure_success(response)


def cancel_runtime_action(
    client: RuntimeClient,
    route_request: RuntimeRouteRequest,
) -> ResponseEnvelope:
    """Cancel a runtime request when the client supports it."""
    request_id = route_request.request_id or str(uuid4())
    try:
        response = client.cancel(request_id)
    except NotImplementedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ensure_success(response)