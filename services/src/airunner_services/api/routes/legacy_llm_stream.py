"""Bounded NDJSON streaming helpers for legacy LLM compatibility routes."""

from __future__ import annotations

import logging
import time

from fastapi.responses import StreamingResponse

from .legacy_contracts import LegacyLLMGenerateRequest
from .legacy_llm_helpers import (
    failed_runtime_response,
    send_legacy_llm_request,
    terminal_stream_message,
    thinking_stream_payload,
    tool_status_stream_payload,
)
from .legacy_llm_observer import (
    LegacyCompletionObserver,
    cancel_owned_llm_request,
)
from .legacy_llm_stream_helpers import stream_payload
from .legacy_llm_stream_payloads import (
    error_payload,
    keepalive_payload,
    ndjson_line,
    timeout_payload,
)


logger = logging.getLogger(__name__)


def stream_callback(observer: LegacyCompletionObserver, action, request_id: str):
    """Return one request-owned callback that queues terminal events last."""

    def callback(data: dict) -> None:
        response = data.get("response")
        if response is None:
            payload = tool_status_stream_payload(data) or thinking_stream_payload(data)
            if payload is not None:
                observer.publish(payload=ndjson_line(payload))
            return
        if getattr(response, "is_system_message", False) and not getattr(
            response, "is_end_of_message", False
        ):
            return
        if failed_runtime_response(response):
            observer.publish(
                payload=error_payload("LLM generation failed", str(action)),
                terminal=True,
                failed=True,
                failure_reason="backend_error",
            )
            return
        payload = stream_payload(response, action)
        message_type = getattr(response, "message_type", None)
        visible_text = (
            payload.get("message", "")
            if message_type in (None, "", "assistant")
            and not getattr(response, "is_system_message", False)
            else ""
        )
        observer.publish(
            payload=ndjson_line(payload),
            text=visible_text,
            terminal=terminal_stream_message(response),
        )

    return callback


def stream_lines(
    observer: LegacyCompletionObserver,
    action_str: str,
):
    """Yield observer events and keepalives until one terminal frame."""
    keepalive_interval = 5.0
    last_yield = time.monotonic()
    try:
        while True:
            event = observer.next_event(timeout=0.25)
            if event is not None:
                if event.payload:
                    yield event.payload
                    last_yield = time.monotonic()
                if event.terminal:
                    return
                continue
            if time.monotonic() - last_yield >= keepalive_interval:
                yield ndjson_line(keepalive_payload(action_str))
                last_yield = time.monotonic()
    finally:
        observer.close()


def build_streaming_response(
    app,
    body: LegacyLLMGenerateRequest,
    prompt: str,
    action,
    llm_request,
    request_id: str,
) -> StreamingResponse:
    """Dispatch and return one bounded request-owned NDJSON stream."""
    action_str = getattr(action, "name", None) or str(action)

    def error_frame(reason: str) -> bytes:
        if reason == "timeout":
            return ndjson_line(timeout_payload(action_str))
        if reason == "overflow":
            message = "Response exceeded the configured output limit"
        else:
            message = "LLM generation failed"
        return error_payload(message, action_str)

    observer = LegacyCompletionObserver(
        request_id,
        error_frame,
        cancel=lambda: cancel_owned_llm_request(app, request_id),
    )
    observer.start_dispatch(
        lambda callback: send_legacy_llm_request(
            app, prompt, action, llm_request, body, request_id, callback
        ),
        stream_callback(observer, action, request_id),
    )
    return StreamingResponse(
        stream_lines(observer, action_str),
        media_type="application/x-ndjson",
    )
