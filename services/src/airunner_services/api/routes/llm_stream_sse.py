"""SSE-streaming LLM endpoint — builds runtime envelope from chat messages."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Iterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from airunner_services.api.routes.llm_runtime import (
    require_runtime_registry,
    resolve_llm_client,
    to_runtime_messages,
)
from airunner_services.api.routes.llm_contracts import ChatCompletionRequest
from airunner_services.ipc.messages import RequestEnvelope, StreamDelta
from airunner_services.runtimes.contracts import (
    LLMInvocationRequest,
    RuntimeAction,
    RuntimeKind,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def _safe_stream_delta(
    iterator: Iterator[StreamDelta],
) -> StreamDelta | None:
    """Return one stream delta or None when exhausted.

    Avoids the Python 3.13 ``RuntimeError`` caused by ``StopIteration``
    bubbling through ``asyncio.to_thread``.
    """

    def _next_or_none() -> StreamDelta | None:
        try:
            return next(iterator)
        except StopIteration:
            return None

    return await asyncio.to_thread(_next_or_none)


@router.post("/conversations/stream")
async def stream_chat_completion(
    payload: ChatCompletionRequest,
    request: Request,
):
    """Stream chat completions as SSE events."""

    async def _stream():
        if not payload.messages:
            yield (
                f"data: {json.dumps({'error': 'No messages', 'done': True})}\n\n"
            )
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
            invocation = LLMInvocationRequest(
                messages=to_runtime_messages(payload.messages),
                model=payload.model,
                temperature=payload.temperature or 0.7,
                max_tokens=payload.max_tokens,
                stream=True,
                metadata={
                    "gguf_runtime_profile": payload.gguf_runtime_profile,
                }
                if payload.gguf_runtime_profile
                else {},
            )
            envelope = RequestEnvelope(
                runtime=RuntimeKind.LLM,
                action=RuntimeAction.INVOKE,
                provider="local",
                stream=True,
                payload=invocation.model_dump(),
            )
            iterator = iter(client.stream(envelope))
            while True:
                stream_delta = await _safe_stream_delta(iterator)
                if stream_delta is None:
                    yield (
                        f"data: {json.dumps({'token': '', 'done': True})}\n\n"
                    )
                    return
                content = stream_delta.delta.get("content", "")
                if content:
                    yield (
                        f"data: {json.dumps({'token': content, 'done': stream_delta.final})}\n\n"
                    )
                if stream_delta.final:
                    yield (
                        f"data: {json.dumps({'token': '', 'done': True})}\n\n"
                    )
                    return
        except Exception as exc:
            logger.exception("SSE stream error")
            yield (
                f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"
            )

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
