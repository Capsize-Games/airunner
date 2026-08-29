"""Non-streaming helpers for legacy LLM compatibility routes."""

import logging
import threading
from typing import Any

from fastapi import HTTPException

from .legacy_contracts import LegacyLLMGenerateRequest
from .legacy_llm_helpers import send_legacy_llm_request, terminal_stream_message

logger = logging.getLogger(__name__)


def collect_callback(
    complete_by_turn: dict[int, list[str]],
    executed_tools: list[str],
    done: threading.Event,
):
    """Return the callback used for non-streaming legacy LLM requests."""

    def callback(data: dict) -> None:
        response = data.get("response")
        if not response:
            return
        turn_index = int(getattr(response, "turn_index", 0) or 0)
        message = getattr(response, "message", "") or ""
        message_type = getattr(response, "message_type", None)
        if message and not getattr(response, "is_system_message", False):
            if message_type == "assistant":
                complete_by_turn.setdefault(turn_index, []).append(message)
        tools = getattr(response, "tools", None)
        if isinstance(tools, (list, tuple, set)):
            executed_tools.extend(str(tool) for tool in tools if tool)
        if terminal_stream_message(response):
            done.set()

    return callback


def collect_non_stream_response(
    app,
    body: LegacyLLMGenerateRequest,
    prompt: str,
    action,
    llm_request,
    request_id: str,
) -> dict[str, Any]:
    """Collect one complete non-streaming legacy LLM response."""
    complete_by_turn: dict[int, list[str]] = {}
    executed_tools: list[str] = []
    done = threading.Event()
    callback = collect_callback(complete_by_turn, executed_tools, done)
    try:
        send_legacy_llm_request(
            app,
            prompt,
            action,
            llm_request,
            body,
            request_id,
            callback,
        )
    except Exception as exc:
        logger.error(
            "Non-streaming LLM request failed (request_id=%s): %s",
            request_id,
            exc,
            exc_info=True,
        )
        # Generic detail only; exception detail stays in the log
        # (CodeQL py/stack-trace-exposure, GitHub issue #2079).
        raise HTTPException(
            status_code=500, detail="Request failed"
        ) from exc
    if not done.wait(timeout=300):
        raise HTTPException(status_code=504, detail="Request timeout")
    final_turn = max(complete_by_turn.keys(), default=0)
    return {
        "message": "".join(complete_by_turn.get(final_turn, [])),
        "tools": list(dict.fromkeys(executed_tools)),
        "tool_calls": list(dict.fromkeys(executed_tools)),
    }