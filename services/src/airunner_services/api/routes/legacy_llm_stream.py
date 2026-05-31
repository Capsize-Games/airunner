"""Streaming helpers for legacy LLM compatibility routes."""

from __future__ import annotations

import logging
import os
import queue
import threading
import time

from fastapi.responses import StreamingResponse

from .legacy_contracts import LegacyLLMGenerateRequest
from .legacy_llm_helpers import send_legacy_llm_request
from .legacy_llm_stream_helpers import (
    action_name,
    handle_stream_event,
    unregister_pending_request,
)
from .legacy_llm_stream_payloads import (
    error_payload,
    keepalive_payload,
    ndjson_line,
    timeout_payload,
)

logger = logging.getLogger(__name__)


def interrupt_llm_async(app) -> None:
    """Interrupt the app LLM in a background thread."""
    try:
        threading.Thread(target=app.llm.interrupt, daemon=True).start()
    except Exception:
        pass


def stream_callback(
    q: queue.Queue[bytes],
    done: threading.Event,
    last_callback_at: list[float],
    action,
    request_id: str,
):
    """Return the callback used for streaming legacy LLM requests."""

    def callback(data: dict) -> None:
        done_now = handle_stream_event(
            data, q, last_callback_at, action, request_id
        )
        if done_now:
            done.set()

    return callback


def _start_background_kickoff(
    app,
    body: LegacyLLMGenerateRequest,
    prompt: str,
    action,
    llm_request,
    request_id: str,
    q: queue.Queue[bytes],
    done: threading.Event,
    action_str: str,
) -> None:
    """Start the background thread that kicks off the legacy LLM stream."""

    def kickoff() -> None:
        try:
            logger.info(
                "llm/generate kickoff send_request start request_id=%s",
                request_id,
            )
            send_legacy_llm_request(
                app, prompt, action, llm_request,
                body, request_id,
                stream_callback(
                    q, done, [time.monotonic()], action, request_id
                ),
            )
            logger.info(
                "llm/generate kickoff send_request returned "
                "request_id=%s",
                request_id,
            )
        except Exception as exc:
            logger.exception(
                "llm/generate kickoff send_request failed "
                "request_id=%s",
                request_id,
            )
            q.put(error_payload(f"Error invoking LLM: {exc}", action_str))
            done.set()

    threading.Thread(target=kickoff, daemon=True).start()


def _idle_timeout_seconds() -> float:
    """Return the configured idle timeout for stream idle detection."""
    try:
        return float(
            os.environ.get(
                "AIRUNNER_LLM_STREAM_IDLE_TIMEOUT_SECONDS", "600"
            )
        )
    except Exception:
        return 600.0




def _cleanup_stream(app, request_id: str, done: threading.Event) -> None:
    """Perform stream cleanup and optional LLM interruption."""
    unregister_pending_request(request_id)
    if not done.is_set():
        logger.warning(
            "llm/generate gen closed early; interrupting request_id=%s",
            request_id,
        )
        interrupt_llm_async(app)
    else:
        logger.info(
            "llm/generate gen cleanup after done; not interrupting "
            "request_id=%s",
            request_id,
        )


def stream_lines(  # noqa: C901
    app,
    q: queue.Queue[bytes],
    done: threading.Event,
    last_callback_at: list[float],
    action_str: str,
    request_id: str,
):
    """Yield streamed NDJSON lines for one legacy LLM request."""
    last_yield = time.monotonic()
    keepalive_interval = 5.0
    idle_timeout = _idle_timeout_seconds()
    logger.info("llm/generate gen start request_id=%s", request_id)
    try:
        while True:
            try:
                line = q.get(timeout=0.25)
                yield line
                last_yield = time.monotonic()
            except queue.Empty:
                now = time.monotonic()
                if done.is_set():
                    logger.info(
                        "llm/generate gen done request_id=%s",
                        request_id,
                    )
                    break
                if now - last_callback_at[0] >= idle_timeout:
                    logger.warning(
                        "llm/generate idle-timeout request_id=%s "
                        "idle=%.1fs timeout=%.1fs",
                        request_id,
                        now - last_callback_at[0],
                        idle_timeout,
                    )
                    yield ndjson_line(
                        timeout_payload(action_str)
                    )
                    done.set()
                    unregister_pending_request(request_id)
                    interrupt_llm_async(app)
                    break
                if now - last_yield >= keepalive_interval:
                    yield ndjson_line(
                        keepalive_payload(action_str)
                    )
                    last_yield = now
    finally:
        _cleanup_stream(app, request_id, done)


def build_streaming_response(
    app,
    body: LegacyLLMGenerateRequest,
    prompt: str,
    action,
    llm_request,
    request_id: str,
) -> StreamingResponse:
    """Return the streaming NDJSON response for one legacy LLM request."""
    q: queue.Queue[bytes] = queue.Queue()
    done = threading.Event()
    last_callback_at = [time.monotonic()]
    action_str = action_name(action, action)
    _start_background_kickoff(
        app, body, prompt, action, llm_request,
        request_id, q, done, action_str,
    )
    return StreamingResponse(
        stream_lines(
            app, q, done, last_callback_at, action_str, request_id
        ),
        media_type="application/x-ndjson",
    )
