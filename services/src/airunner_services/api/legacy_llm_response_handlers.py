"""LLM response handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import inspect
import json
import threading
from typing import Any, Callable, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest


def handle_llm_stream(
    handler: Any,
    prompt: str,
    action: LLMActionType,
    llm_request: LLMRequest,
    request_id: str,
    *,
    get_api: Callable[..., Any],
    search_hints: Optional[dict[str, Any]] = None,
) -> None:
    """Handle one streaming LLM response as NDJSON."""
    handler._set_headers(200, content_type="application/x-ndjson")
    complete_event = threading.Event()
    callback = _stream_callback(handler, complete_event, action)
    api = get_api()
    if not _send_stream_request(
        handler,
        api,
        prompt,
        action,
        llm_request,
        request_id,
        callback,
        search_hints,
    ):
        return
    _wait_for_stream_completion(handler, complete_event, request_id)
    handler.close_connection = True


def _stream_callback(
    handler: Any,
    complete_event: threading.Event,
    action: LLMActionType,
) -> Callable[[dict[str, Any]], None]:
    """Return the callback that writes stream chunks to the client."""

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        _log_stream_chunk(handler, response)
        _write_ndjson_line(
            handler,
            _stream_response_data(response, action),
        )
        if response.is_end_of_message:
            complete_event.set()

    return callback


def _log_stream_chunk(handler: Any, response: Any) -> None:
    """Best-effort debug logging for one stream callback payload."""
    try:
        handler.logger.debug(
            "HTTP Server: stream_callback invoked: msg_len=%s, "
            "is_end=%s, seq=%s",
            len(response.message) if response and response.message else 0,
            response.is_end_of_message,
            getattr(response, "sequence_number", None),
        )
    except Exception:
        return


def _stream_response_data(
    response: Any,
    action: LLMActionType,
) -> dict[str, Any]:
    """Build the NDJSON payload for one stream chunk."""
    return {
        "message": response.message,
        "is_first_message": response.is_first_message,
        "is_end_of_message": response.is_end_of_message,
        "sequence_number": getattr(response, "sequence_number", 0),
        "action": _action_name(getattr(response, "action", None), action),
        "tools": getattr(response, "tools", None),
        "error": bool(getattr(response, "is_system_message", False)),
        "is_system_message": bool(
            getattr(response, "is_system_message", False)
        ),
    }


def _action_name(response_action: Any, action: LLMActionType) -> str:
    """Return the serialized action name for one response."""
    if response_action is not None:
        if hasattr(response_action, "value"):
            return str(response_action.value)
        return str(response_action)
    if hasattr(action, "value"):
        return str(action.value)
    return str(action)


def _write_ndjson_line(handler: Any, payload: dict[str, Any]) -> None:
    """Write one NDJSON payload to the HTTP response stream."""
    handler.wfile.write(json.dumps(payload).encode("utf-8") + b"\n")
    handler.wfile.flush()


def _send_stream_request(
    handler: Any,
    api: Any,
    prompt: str,
    action: LLMActionType,
    llm_request: LLMRequest,
    request_id: str,
    callback: Callable[[dict[str, Any]], None],
    search_hints: Optional[dict[str, Any]],
) -> bool:
    """Send one streaming request to the LLM service."""
    handler.logger.debug(
        "Sending to API with llm_request.max_new_tokens=%s",
        llm_request.max_new_tokens,
    )
    handler.logger.info(
        "HTTP Server: send_request file: %s",
        inspect.getfile(api.llm.send_request),
    )
    handler.logger.info(
        "HTTP Server: About to call api.llm.send_request, api type=%s, "
        "api.llm type=%s",
        type(api),
        type(api.llm),
    )
    try:
        api.llm.send_request(
            prompt=prompt,
            action=action,
            llm_request=llm_request,
            request_id=request_id,
            callback=callback,
            search_hints=search_hints,
        )
    except Exception as error:
        handler.logger.error(
            "HTTP Server: Exception calling send_request: %s",
            error,
            exc_info=True,
        )
        _write_stream_error(handler, f"Error invoking LLM: {error}")
        return False
    handler.logger.debug("HTTP Server: send_request returned (non-blocking)")
    handler.logger.info(
        "HTTP Server: api.llm.send_request completed successfully"
    )
    return True


def _write_stream_error(handler: Any, message: str) -> None:
    """Write one terminal NDJSON error payload."""
    try:
        _write_ndjson_line(
            handler,
            {
                "message": message,
                "is_first_message": True,
                "is_end_of_message": True,
                "sequence_number": 0,
                "error": True,
            },
        )
    except Exception:
        return


def _wait_for_stream_completion(
    handler: Any,
    complete_event: threading.Event,
    request_id: str,
) -> None:
    """Wait for one stream request to finish or time out."""
    handler.logger.debug(
        "HTTP Server: Waiting for completion event with timeout %ss "
        "(request_id=%s)",
        handler._timeout,
        request_id,
    )
    if complete_event.wait(timeout=handler._timeout):
        handler.logger.debug(
            "HTTP Server: complete_event set for request_id=%s",
            request_id,
        )
        return
    _write_stream_error(handler, "Request timeout")


def handle_llm_non_stream(
    handler: Any,
    prompt: str,
    action: LLMActionType,
    llm_request: LLMRequest,
    request_id: str,
    *,
    get_api: Callable[..., Any],
    search_hints: Optional[dict[str, Any]] = None,
) -> None:
    """Handle one non-streaming LLM response as a single JSON object."""
    handler.logger.debug(
        "_handle_llm_non_stream ENTERED with request_id=%s",
        request_id,
    )
    complete_message_by_turn: dict[int, list[str]] = {}
    executed_tools: list[Any] = []
    complete_event = threading.Event()
    callback = _collect_non_stream_callback(
        handler,
        complete_message_by_turn,
        executed_tools,
        complete_event,
    )
    handler.logger.debug(
        "HTTP Server Registering callback %s for request %s",
        id(callback),
        request_id,
    )
    handler.logger.debug("HTTP Server Event object: %s", id(complete_event))
    handler.logger.debug("HTTP Server About to call api.llm.send_request...")
    api = get_api()
    api.llm.send_request(
        prompt=prompt,
        action=action,
        llm_request=llm_request,
        request_id=request_id,
        callback=callback,
        search_hints=search_hints,
    )
    handler.logger.debug("HTTP Server api.llm.send_request completed")
    handler.logger.debug(
        "HTTP Server Waiting for event %s with %ss timeout...",
        id(complete_event),
        handler._timeout,
    )
    handler._send_json_response(
        _non_stream_response(
            complete_event,
            complete_message_by_turn,
            executed_tools,
            action,
            handler._timeout,
        )
    )


def _collect_non_stream_callback(
    handler: Any,
    complete_message_by_turn: dict[int, list[str]],
    executed_tools: list[Any],
    complete_event: threading.Event,
) -> Callable[[dict[str, Any]], None]:
    """Return the callback used for non-streaming LLM requests."""

    def callback(data: dict[str, Any]) -> None:
        handler.logger.debug(
            "HTTP Callback %s CALLED with data keys: %s",
            id(callback),
            list(data.keys()),
        )
        response = data.get("response")
        handler.logger.debug(
            "HTTP Callback Response type: %s, is_end: %s",
            type(response),
            response.is_end_of_message if response else None,
        )
        handler.logger.info(
            "HTTP Callback Received response: message_len=%s, is_end=%s",
            len(response.message) if response else 0,
            response.is_end_of_message if response else None,
        )
        if not response:
            return
        _collect_turn_message(complete_message_by_turn, response)
        _collect_tools(handler, executed_tools, response)
        if response.is_end_of_message:
            _mark_non_stream_complete(handler, complete_event)

    return callback


def _collect_turn_message(
    complete_message_by_turn: dict[int, list[str]],
    response: Any,
) -> None:
    """Collect one visible assistant chunk for the final turn response."""
    turn_index = int(getattr(response, "turn_index", 0) or 0)
    message_type = getattr(response, "message_type", None)
    if not response.message:
        return
    if getattr(response, "is_system_message", False):
        return
    if message_type == "system":
        return
    complete_message_by_turn.setdefault(turn_index, []).append(response.message)


def _collect_tools(
    handler: Any,
    executed_tools: list[Any],
    response: Any,
) -> None:
    """Collect tool names emitted during one non-stream request."""
    if hasattr(response, "tools") and response.tools:
        handler.logger.info(
            "HTTP Callback Tools found in response: %s",
            response.tools,
        )
        executed_tools.extend(response.tools)
        return
    if response.is_end_of_message:
        handler.logger.warning(
            "HTTP Callback End of message but no tools. "
            "has_tools_attr=%s, tools_value=%s",
            hasattr(response, "tools"),
            getattr(response, "tools", None),
        )


def _mark_non_stream_complete(
    handler: Any,
    complete_event: threading.Event,
) -> None:
    """Mark one non-stream request as complete in the logs and event."""
    handler.logger.debug(
        "HTTP Callback END OF MESSAGE - setting event %s",
        id(complete_event),
    )
    handler.logger.info(
        "HTTP Callback End of message detected, setting event"
    )
    complete_event.set()
    handler.logger.debug(
        "HTTP Callback Event set: %s",
        complete_event.is_set(),
    )


def _non_stream_response(
    complete_event: threading.Event,
    complete_message_by_turn: dict[int, list[str]],
    executed_tools: list[Any],
    action: LLMActionType,
    timeout: float,
) -> dict[str, Any]:
    """Return the final non-stream HTTP payload."""
    if not complete_event.wait(timeout=timeout):
        return {
            "message": "Request timeout",
            "is_first_message": True,
            "is_end_of_message": True,
            "sequence_number": 0,
            "error": True,
            "tools": [],
        }

    final_turn = max(complete_message_by_turn.keys(), default=0)
    final_message = "".join(complete_message_by_turn.get(final_turn, []))
    return {
        "message": final_message,
        "is_first_message": True,
        "is_end_of_message": True,
        "sequence_number": 0,
        "action": action.value if hasattr(action, "value") else str(action),
        "tools": list(dict.fromkeys(executed_tools)),
    }