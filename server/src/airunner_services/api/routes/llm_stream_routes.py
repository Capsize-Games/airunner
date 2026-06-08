"""Websocket streaming routes for runtime-backed LLM endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .llm_runtime import (
    require_websocket_runtime_registry,
    resolve_llm_client,
    stream_runtime,
    websocket_chunk,
    websocket_envelope,
)

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


async def _stream_to_socket(client, websocket: WebSocket, envelope) -> None:
    """Stream all deltas for one request to the websocket."""
    async for delta in stream_runtime(client, envelope):
        await websocket.send_json(websocket_chunk(delta))
        if delta.final:
            break


@router.websocket("/stream")
async def websocket_chat(websocket: WebSocket):
    """Stream chat responses from the runtime-backed local LLM."""
    await websocket.accept()
    try:
        client = resolve_llm_client(
            require_websocket_runtime_registry(websocket)
        )
        while True:
            data = await websocket.receive_json()

            # Handle cancel for any previously running stream (belt-and-suspenders;
            # the concurrent cancel below is the primary mechanism).
            if data.get("type") == "cancel":
                continue

            has_content = bool(str(data.get("message", "")).strip()) or bool(
                data.get("messages")
            )
            if not has_content:
                await websocket.send_json(
                    {"type": "error", "content": "No message provided"}
                )
                continue

            stream_task: asyncio.Task = asyncio.create_task(
                _stream_to_socket(client, websocket, websocket_envelope(data))
            )
            # Race the stream against an incoming cancel message so the client
            # can abort mid-generation without waiting for the full response.
            cancel_task: asyncio.Task = asyncio.create_task(
                websocket.receive_json()
            )

            done, pending = await asyncio.wait(
                {stream_task, cancel_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if cancel_task in done and not cancel_task.cancelled():
                incoming = cancel_task.result()
                if incoming.get("type") == "cancel":
                    stream_task.cancel()
                    try:
                        await stream_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    await websocket.send_json({"type": "done", "done": True})
                else:
                    # Non-cancel message arrived during streaming — wait for
                    # the current stream to finish, then process it next turn.
                    for t in pending:
                        t.cancel()
                        try:
                            await t
                        except (asyncio.CancelledError, Exception):
                            pass
            else:
                # Stream completed before any cancel arrived.
                cancel_task.cancel()
                try:
                    await cancel_task
                except (asyncio.CancelledError, Exception):
                    pass

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except HTTPException as exc:
        await websocket.send_json(
            {"type": "error", "content": exc.detail, "done": True}
        )
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        await websocket.send_json(
            {
                "type": "error",
                "content": f"Server error: {str(exc)}",
                "done": True,
            }
        )
