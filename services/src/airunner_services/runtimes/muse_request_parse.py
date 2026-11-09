"""Request parsing for the Muse cloud art runtime client."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from airunner_services.runtimes.contracts import (
    ArtInvocationRequest, RuntimeKind,
)


def parse_muse_request(
    request: Any,
) -> tuple[str, Optional[ArtInvocationRequest]]:
    """Return (request_id, invocation) for one Muse request."""
    if isinstance(request, ArtInvocationRequest):
        return f"muse-{uuid4().hex}", request
    provider = getattr(request, "provider", None)
    if provider not in (None, "", "muse"):
        raise ValueError("MuseArtClient only supports muse")
    if getattr(request, "runtime", RuntimeKind.ART) is not RuntimeKind.ART:
        raise ValueError("MuseArtClient only supports art")
    payload = getattr(request, "payload", {})
    request_id = str(getattr(request, "request_id", "") or "")
    request_id = request_id or f"muse-{uuid4().hex}"
    if isinstance(payload, ArtInvocationRequest):
        return request_id, payload
    if payload in (None, {}):
        return request_id, None
    if not isinstance(payload, dict):
        raise ValueError("Muse payload must be an object")
    return request_id, ArtInvocationRequest.model_validate(payload)


__all__ = ["parse_muse_request"]
