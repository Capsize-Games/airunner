"""Legacy compatibility routes for LLM generation."""

import logging
import os
import uuid

from fastapi import APIRouter, HTTPException, Request

from airunner_services.api.models.runtime_route_request import (
    RuntimeRouteRequest,
)
from airunner_services.api.routes.daemon_helpers import (
    ensure_vram_available_for,
)
from airunner_services.runtimes.contracts import RuntimeKind

from .legacy_common import get_airunner_app
from .legacy_contracts import LegacyLLMGenerateRequest
from .legacy_llm_helpers import build_llm_request, parse_action
from .legacy_llm_nonstream import collect_non_stream_response
from .legacy_llm_stream import build_streaming_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/llm/generate")
def legacy_llm_generate(body: LegacyLLMGenerateRequest, req: Request):
    """Serve the legacy NDJSON LLM streaming endpoint."""
    app = get_airunner_app(req)
    os.environ.setdefault("AIRUNNER_HEADLESS", "1")
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' field")
    action = parse_action(body.action)
    request_id = (req.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
    llm_request = build_llm_request(body.model_dump())
    if body.system_prompt:
        llm_request.system_prompt = body.system_prompt
    logger.info(
        "llm/generate received request_id=%s stream=%s prompt_len=%d action=%s",
        request_id,
        bool(body.stream),
        len(prompt),
        str(getattr(action, "name", None) or getattr(action, "value", action)),
    )
    ensure_vram_available_for(
        req,
        RuntimeRouteRequest(provider="local", request_id=request_id),
        RuntimeKind.LLM,
    )
    if not body.stream:
        return collect_non_stream_response(
            app,
            body,
            prompt,
            action,
            llm_request,
            request_id,
        )
    return build_streaming_response(
        app,
        body,
        prompt,
        action,
        llm_request,
        request_id,
    )