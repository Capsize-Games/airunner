"""Non-streaming helpers for legacy LLM compatibility routes."""

import logging
from typing import Any

from fastapi import HTTPException

from .legacy_contracts import LegacyLLMGenerateRequest
from .legacy_llm_helpers import (
    failed_runtime_response,
    send_legacy_llm_request,
    terminal_stream_message,
)
from .legacy_llm_observer import (
    LegacyCompletionObserver,
    cancel_owned_llm_request,
)
from .legacy_llm_stream_payloads import error_payload

logger = logging.getLogger(__name__)


def collect_callback(
    observer: LegacyCompletionObserver,
):
    """Return the callback used for non-streaming legacy LLM requests."""

    def callback(data: dict) -> None:
        response = data.get("response")
        if not response:
            return
        if failed_runtime_response(response):
            observer.publish(
                terminal=True,
                failed=True,
                failure_reason="backend_error",
            )
            return
        turn_index = int(getattr(response, "turn_index", 0) or 0)
        message = getattr(response, "message", "") or ""
        message_type = getattr(response, "message_type", None)
        if message and not getattr(response, "is_system_message", False):
            if message_type == "assistant":
                text = message
            else:
                text = ""
        else:
            text = ""
        tools = getattr(response, "tools", None)
        tool_names: tuple[str, ...] = ()
        if isinstance(tools, (list, tuple, set)):
            tool_names = tuple(str(tool) for tool in tools if tool)
        observer.publish(
            text=text,
            turn_index=turn_index,
            tools=tool_names,
            terminal=terminal_stream_message(response),
        )

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
    action_name = getattr(action, "name", None) or str(action)
    observer = LegacyCompletionObserver(
        request_id,
        lambda reason: error_payload(
            "Request timeout" if reason == "timeout" else "LLM generation failed",
            action_name,
        ),
        cancel=lambda: cancel_owned_llm_request(app, request_id),
    )
    observer.start_dispatch(
        lambda callback: send_legacy_llm_request(
            app, prompt, action, llm_request, body, request_id, callback
        ),
        collect_callback(observer),
    )
    try:
        events = observer.collect()
    finally:
        observer.close()
    terminal = events[-1]
    if terminal.failed:
        if terminal.failure_reason == "timeout":
            raise HTTPException(status_code=504, detail="Request timeout")
        raise HTTPException(status_code=500, detail="LLM generation failed")
    complete_by_turn: dict[int, list[str]] = {}
    executed_tools: list[str] = []
    for event in events:
        if event.text:
            complete_by_turn.setdefault(event.turn_index, []).append(event.text)
        executed_tools.extend(event.tools)
    final_turn = max(complete_by_turn.keys(), default=0)
    return {
        "message": "".join(complete_by_turn.get(final_turn, [])),
        "tools": list(dict.fromkeys(executed_tools)),
        "tool_calls": list(dict.fromkeys(executed_tools)),
    }
