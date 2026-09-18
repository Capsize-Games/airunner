"""Websocket streaming routes for runtime-backed LLM endpoints."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import ValidationError

from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .llm_chat_envelope import is_client_chat, stream_client_chat
from .llm_contracts import (
    LLMStreamValidationError,
    WebSocketRateLimiter,
    default_rate_limit_max_requests,
    default_rate_limit_window_seconds,
    hash_principal,
    parse_stream_message,
)
from .llm_runtime import (
    require_websocket_runtime_registry,
    resolve_llm_client,
    stream_runtime,
    websocket_chunk,
    websocket_envelope,
)

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

# Module-level so admission state survives a client's reconnect: a fresh
# WebSocket object per connection must not reset the caller's budget.
_rate_limiter = WebSocketRateLimiter(
    max_requests=default_rate_limit_max_requests(),
    window_seconds=default_rate_limit_window_seconds(),
)


def _resolve_principal(websocket: WebSocket) -> str:
    """Return a stable id for the caller authenticate_connection() admitted.

    Derived from whichever credential actually gated this connection, so
    the same credential always yields the same principal across
    reconnects without duplicating server.py's auth branching here.
    """
    state = websocket.app.state
    if getattr(state, "require_api_key", False):
        return hash_principal("api_key", getattr(state, "api_key", ""))
    if getattr(state, "insecure_no_auth", False):
        client = getattr(websocket, "client", None)
        host = getattr(client, "host", "") if client else "unknown"
        return hash_principal("insecure", host)
    from airunner_services.api.loopback_token import (
        get_or_create_loopback_token,
    )

    return hash_principal("loopback", get_or_create_loopback_token())


def _websocket_auth_error(websocket: WebSocket) -> bool:
    """Return True when the socket fails the API-key/loopback/origin policy.

    Applied before ``accept()`` and before any runtime resolution so an
    unauthenticated or unapproved-Origin caller never reaches the LLM
    runtime, matching the HTTP API's existing auth policy.
    """
    # Imported lazily: server.py's module-level route imports transitively
    # import this file, so a top-level import here would be circular.
    from airunner_services.api.server import (
        authenticate_connection,
        is_allowed_origin,
    )

    state = websocket.app.state
    origin = websocket.headers.get("origin")
    if origin and not is_allowed_origin(
        origin, getattr(state, "allowed_origins", [])
    ):
        return True

    allowed, _status_code = authenticate_connection(
        websocket,
        api_key=getattr(state, "api_key", ""),
        require_api_key=getattr(state, "require_api_key", False),
        insecure_no_auth=getattr(state, "insecure_no_auth", False),
    )
    return not allowed


@router.websocket("/stream")
async def websocket_chat(websocket: WebSocket):
    """Stream chat responses from the runtime-backed local LLM."""
    if _websocket_auth_error(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    principal = _resolve_principal(websocket)
    try:
        client = resolve_llm_client(require_websocket_runtime_registry(websocket))
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                # Malformed JSON (json.JSONDecodeError, a ValueError
                # subclass): reject with the same deterministic
                # invalid_request code as a structurally-wrong-but-valid
                # -JSON payload, and keep the connection open, instead of
                # falling through to the generic exception handler below
                # (which would close the connection on every parse error).
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_request",
                        "content": "Invalid request",
                        "done": True,
                    }
                )
                continue

            if not _rate_limiter.allow(principal):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "rate_limited",
                        "content": "Rate limit exceeded",
                        "done": True,
                    }
                )
                continue

            if is_client_chat(data):
                await stream_client_chat(websocket, client, data)
                continue

            try:
                parsed = parse_stream_message(data)
            except ValidationError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_request",
                        "content": "Invalid request",
                        "done": True,
                    }
                )
                continue
            except LLMStreamValidationError as exc:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": exc.code,
                        "content": "Request rejected",
                        "done": True,
                    }
                )
                continue

            async for delta in stream_runtime(
                client, websocket_envelope(parsed.model_dump())
            ):
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
        logger.error("WebSocket error: %s", exc, exc_info=True)
        await websocket.send_json(
            {
                "type": "error",
                # Generic message only; exception detail stays in the log
                # (CodeQL py/stack-trace-exposure, GitHub issue #2079).
                "content": "Server error",
                "done": True,
            }
        )