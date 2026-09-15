"""Stream processing utilities for legacy LLM compatibility routes."""

from __future__ import annotations

import logging
import queue
import time

from airunner_services.utils.application.signal_mediator import SignalMediator

from .legacy_llm_helpers import (
    terminal_stream_message,
    thinking_stream_payload,
    tool_status_stream_payload,
)
from .legacy_llm_stream_payloads import ndjson_line

logger = logging.getLogger(__name__)


def response_usage(response) -> dict | None:
    """Return token-usage metadata when the response exposes it."""
    try:
        prompt_tokens = getattr(response, "prompt_tokens", None)
        completion_tokens = getattr(
            response, "completion_tokens", None
        )
        total_tokens = getattr(response, "total_tokens", None)
        if (
            prompt_tokens is None
            and completion_tokens is None
            and total_tokens is None
        ):
            return None
        return {
            "prompt_tokens": (
                int(prompt_tokens) if prompt_tokens is not None
                else None
            ),
            "completion_tokens": (
                int(completion_tokens)
                if completion_tokens is not None
                else None
            ),
            "total_tokens": (
                int(total_tokens) if total_tokens is not None
                else None
            ),
        }
    except Exception:
        return None


def action_name(action_value, fallback) -> str:
    """Return one string action name for streamed legacy responses."""
    return str(
        getattr(action_value, "name", None)
        or getattr(action_value, "value", action_value or fallback)
    )


def stream_payload(response, action) -> dict:
    """Build one streamed NDJSON payload from an LLM callback response."""
    action_value = getattr(response, "action", None) or action
    payload = {
        "message": getattr(response, "message", "") or "",
        "is_first_message": bool(
            getattr(response, "is_first_message", False)
        ),
        "is_end_of_message": bool(
            getattr(response, "is_end_of_message", False)
        ),
        "done": bool(getattr(response, "is_end_of_message", False)),
        "sequence_number": int(
            getattr(response, "sequence_number", 0) or 0
        ),
        "turn_index": int(
            getattr(response, "turn_index", 0) or 0
        ),
        "message_type": getattr(response, "message_type", None),
        "action": action_name(action_value, action),
        "tool_calls": getattr(response, "tools", None),
        "tools": getattr(response, "tools", None),
        "error": bool(getattr(response, "is_system_message", False)),
        "is_system_message": bool(
            getattr(response, "is_system_message", False)
        ),
    }
    usage = response_usage(response)
    if usage is not None and payload["is_end_of_message"]:
        payload["usage"] = usage
    return payload


def unregister_pending_request(request_id: str) -> None:
    """Remove one pending request from the shared signal mediator."""
    try:
        SignalMediator().unregister_pending_request(request_id)
    except Exception:
        pass


def handle_non_response_event(
    data: dict,
    q: queue.Queue[bytes],
    last_callback_at: list[float],
) -> None:
    """Publish a tool-status or thinking event if present."""
    payload = tool_status_stream_payload(data) or (
        thinking_stream_payload(data)
    )
    if payload is None:
        return
    last_callback_at[0] = time.monotonic()
    q.put(ndjson_line(payload))


def is_suppressed_system_message(response) -> bool:
    """Return True when a system message should be suppressed."""
    try:
        return bool(
            getattr(response, "is_system_message", False)
            and not getattr(response, "is_end_of_message", False)
        )
    except Exception:
        return False


def publish_response_event(
    response,
    action,
    q: queue.Queue[bytes],
    last_callback_at: list[float],
    request_id: str,
) -> None:
    """Build and publish one streamed response payload."""
    last_callback_at[0] = time.monotonic()
    payload = stream_payload(response, action)
    q.put(ndjson_line(payload))
    if payload["sequence_number"] in (0, 1) or payload[
        "is_end_of_message"
    ]:
        logger.info(
            "llm/generate stream_cb request_id=%s seq=%s done=%s "
            "msg_len=%d",
            request_id,
            payload["sequence_number"],
            payload["is_end_of_message"],
            len(payload.get("message") or ""),
        )


def handle_stream_event(
    data: dict,
    q: queue.Queue[bytes],
    last_callback_at: list[float],
    action,
    request_id: str,
) -> bool:
    """Process one stream callback event; return True if stream done."""
    response = data.get("response")
    if response is None:
        handle_non_response_event(data, q, last_callback_at)
        return False
    if is_suppressed_system_message(response):
        return False
    publish_response_event(
        response, action, q, last_callback_at, request_id
    )
    if terminal_stream_message(response):
        unregister_pending_request(request_id)
        return True
    return False
