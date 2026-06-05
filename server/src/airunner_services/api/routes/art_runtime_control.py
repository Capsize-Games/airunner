"""Control-request helpers for art API routes."""

import asyncio
import secrets
from typing import Optional

from fastapi import HTTPException, Request

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind

from .art_runtime_llm import unload_llm_before_art
from .art_runtime_registry import require_runtime_registry, resolve_art_client

# Control request construction


def response_status_is(response: object, expected: EnvelopeStatus) -> bool:
    """Return True when one envelope-like response matches a status."""
    status = getattr(response, "status", None)
    value = getattr(status, "value", status)
    return str(value or "").strip().lower() == expected.value


def control_metadata(
    component: Optional[str],
    metadata: Optional[dict],
) -> dict:
    """Return normalized control metadata for one art request."""
    request_metadata = dict(metadata or {})
    if component is not None:
        request_metadata["component"] = component
    return request_metadata


def build_control_request(
    action: RuntimeAction,
    payload: Optional[dict],
    metadata: Optional[dict],
) -> RequestEnvelope:
    """Build one non-job art control request envelope."""
    return RequestEnvelope(
        request_id=secrets.token_urlsafe(12),
        runtime=RuntimeKind.ART,
        action=action,
        payload=payload or {},
        metadata=metadata or {},
    )


def response_error_detail(response: object) -> str:
    """Return one normalized error detail from an art control response."""
    error = getattr(response, "error", None)
    return getattr(error, "message", None) or "Art runtime request failed"


def unload_required(action: RuntimeAction) -> bool:
    """Return True when one control action needs LLM VRAM to be freed."""
    return action in (RuntimeAction.INVOKE, RuntimeAction.LOAD_MODEL)


async def control_response(
    req: Request,
    action: RuntimeAction,
    component: Optional[str],
    payload: Optional[dict],
    metadata: Optional[dict],
):
    """Return the raw runtime response for one art control request."""
    client = resolve_art_client(require_runtime_registry(req))
    return await asyncio.to_thread(
        client.invoke,
        build_control_request(
            action,
            payload,
            control_metadata(component, metadata),
        ),
    )


def require_successful_control(response: object):
    """Return one control response or raise when the runtime failed."""
    if response_status_is(response, EnvelopeStatus.SUCCEEDED):
        return response
    raise HTTPException(
        status_code=500, detail=response_error_detail(response)
    )


async def invoke_art_control(
    req: Request,
    *,
    action: RuntimeAction,
    component: Optional[str] = None,
    payload: Optional[dict] = None,
    metadata: Optional[dict] = None,
):
    """Invoke one non-job art runtime request."""
    if unload_required(action):
        await unload_llm_before_art(req, source=f"art_{action.value}")
    response = await control_response(
        req,
        action,
        component,
        payload,
        metadata,
    )
    return require_successful_control(response)
