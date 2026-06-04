"""Websocket streaming routes for runtime-backed LLM endpoints."""

from __future__ import annotations

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


@router.websocket("/stream")
async def websocket_chat(websocket: WebSocket):
    """Stream chat responses from the runtime-backed local LLM."""
    await websocket.accept()
    try:
        client = resolve_llm_client(require_websocket_runtime_registry(websocket))
        while True:
            data = await websocket.receive_json()
            prompt = str(data.get("message", "")).strip()
            if not prompt:
                await websocket.send_json(
                    {"type": "error", "content": "No message provided"}
                )
                continue
            async for delta in stream_runtime(client, websocket_envelope(data)):
                await websocket.send_json(websocket_chunk(delta))
                if delta.final:
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except HTTPException as exc:
        await websocket.send_json(
            {"type": "error", "content": exc.detail, "done": True}
        )
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
        await websocket.send_json(
            {
                "type": "error",
                "content": f"Server error: {str(exc)}",
                "done": True,
            }
        )