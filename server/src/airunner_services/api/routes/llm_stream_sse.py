"""SSE-streaming LLM endpoint — routes through the app LLM pipeline."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from airunner_services.api.routes.legacy_common import get_airunner_app
from airunner_services.api.routes.legacy_llm_stream_helpers import (
    handle_stream_event,
)
from airunner_services.api.routes.legacy_llm_stream_payloads import (
    error_payload,
)
from airunner_services.api.routes.llm_contracts import ChatCompletionRequest
from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest

router = APIRouter()
logger = logging.getLogger(__name__)

_IDLE_TIMEOUT_SECONDS = 0.1
_MIN_IDLE_CHECK_SECONDS = 0.025


def _build_llm_request(payload: ChatCompletionRequest) -> LLMRequest:
    """Build an LLMRequest from the SSE chat completion payload."""
    llm_request = LLMRequest()
    if payload.model:
        llm_request.model = payload.model
    if payload.temperature is not None:
        llm_request.temperature = payload.temperature
    if payload.max_tokens is not None:
        llm_request.max_new_tokens = payload.max_tokens
    if payload.llm_overrides:
        llm_request.llm_overrides = payload.llm_overrides
    # Resolve active document IDs to file paths for RAG
    if payload.active_document_ids:
        from airunner_services.database.models.document import Document
        from airunner_services.database.session import session_scope
        with session_scope() as session:
            docs = (
                session.query(Document)
                .filter(Document.id.in_(payload.active_document_ids))
                .all()
            )
            paths = [doc.path for doc in docs if doc.active]
            if paths:
                llm_request.rag_files = paths
    return llm_request


def _extract_prompt(messages: list) -> str:
    """Extract the last user message as the prompt string."""
    for msg in reversed(messages):
        role = getattr(msg, "role", None)
        if role and str(role).lower() in ("user", "human"):
            return getattr(msg, "content", "") or ""
    return ""


def _sse_line(chunk: bytes) -> bytes:
    """Wrap one NDJSON chunk as an SSE data line."""
    return b"data: " + chunk


def _ndjson_to_sse_token(chunk: bytes) -> bytes | None:
    """Convert legacy NDJSON chunk to SSE token format.

    The legacy sender transmits the full accumulated text in the
    ``message`` field each time.  We forward it as-is so the client
    can replace (not append) its local buffer, matching the behaviour
    of the PySide6 ``updateLastMessageContent`` callback.
    """
    try:
        obj = json.loads(chunk.decode("utf-8").rstrip("\n"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if obj.get("keepalive"):
        return None

    token = obj.get("message", "") or ""
    done = bool(obj.get("is_end_of_message") or obj.get("done"))
    msg_type = obj.get("message_type", "") or ""

    payload: dict = {"token": token, "done": done}
    # Thinking ends only that particular segment — suppress done
    # so the client keeps reading for the real chat response.
    if msg_type and msg_type.strip().lower() == "thinking":
        payload["done"] = False
    if msg_type:
        payload["message_type"] = msg_type
    return _sse_line(json.dumps(payload).encode("utf-8") + b"\n")


@router.post("/conversations/stream")
def stream_chat_completion(
    payload: ChatCompletionRequest,
    request: Request,
):
    """Stream chat completions through the app LLM pipeline."""
    messages = payload.messages or []
    prompt = _extract_prompt(messages)
    if not prompt:
        raise HTTPException(
            status_code=400, detail="No user message found",
        )

    app = get_airunner_app(request)
    llm_request = _build_llm_request(payload)
    request_id = (
        request.headers.get("x-request-id", "").strip()
        or str(uuid.uuid4())
    )

    q: queue.Queue[bytes] = queue.Queue()
    done = threading.Event()
    last_callback_at = [time.monotonic()]
    action = LLMActionType.CHAT

    # Apply per-preset overrides when the client sent them
    if llm_request.llm_overrides:
        from airunner_services.api.routes.llm_settings_presets import (
            _PRESET_LABELS,
        )
        label = _PRESET_LABELS.get(action)
        if label:
            llm_request.merge_preset_overrides(
                llm_request.llm_overrides, label
            )

    def callback(data: dict) -> None:
        done_now = handle_stream_event(
            data, q, last_callback_at, action, request_id,
        )
        if done_now:
            done.set()

    def kickoff() -> None:
        try:
            app.llm.send_request(
                prompt=prompt,
                action=action,
                llm_request=llm_request,
                request_id=request_id,
                callback=callback,
                do_tts_reply=False,
            )
        except Exception as exc:
            logger.exception(
                "SSE LLM request failed request_id=%s", request_id,
            )
            q.put(error_payload(str(exc), "CHAT"))
            done.set()

    threading.Thread(target=kickoff, daemon=True).start()

    def event_stream():
        while True:
            try:
                chunk = q.get(timeout=_IDLE_TIMEOUT_SECONDS)
                sse_chunk = _ndjson_to_sse_token(chunk)
                if sse_chunk is not None:
                    yield sse_chunk
            except queue.Empty:
                if done.is_set():
                    yield _sse_line(
                        json.dumps({
                            "token": "",
                            "done": True,
                        }).encode("utf-8") + b"\n",
                    )
                    return
                time.sleep(_MIN_IDLE_CHECK_SECONDS)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
