"""SSE-streaming LLM endpoint using the existing runtime infrastructure."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from airunner_services.api.routes.llm_runtime import (
    require_runtime_registry,
    resolve_llm_client,
    stream_runtime,
    to_runtime_messages,
    websocket_envelope,
)
from airunner_services.api.routes.llm_contracts import ChatCompletionRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/conversations/stream")
async def stream_chat_completion(
    payload: ChatCompletionRequest,
    request: Request,
):
    """Stream chat completions as SSE events."""

    async def _stream():
        if not payload.messages:
            yield f"data: {json.dumps({'error': 'No messages', 'done': True})}\n\n"
            return
        try:
            client = resolve_llm_client(
                require_runtime_registry(request),
            )
        except HTTPException as exc:
            yield (
                f"data: {json.dumps({'error': exc.detail, 'done': True})}\n\n"
            )
            return
        try:
            envelope = websocket_envelope(
                {"messages": payload.messages},
            )
            async for stream_delta in stream_runtime(client, envelope):
                content = stream_delta.delta.get("content", "")
                if content:
                    yield (
                        f"data: {json.dumps({'token': content, 'done': stream_delta.final})}\n\n"
                    )
                if stream_delta.final:
                    yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
        except Exception as exc:
            logger.exception("SSE stream error")
            yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
