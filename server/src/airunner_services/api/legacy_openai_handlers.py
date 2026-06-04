"""OpenAI-compatible handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Callable

from airunner_services.contract_enums import LLMActionType

from airunner_services.api.legacy_openai_helpers import (
    build_usage,
    create_llm_request,
    enhance_system_prompt,
    extract_prompt_and_system,
    parse_tool_calls_from_response,
)


def handle_openai_models(handler: Any, _data: Any) -> None:
    """Handle OpenAI /v1/models endpoint."""
    handler._send_json_response(
        {
            "object": "list",
            "data": [
                {
                    "id": "airunner",
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": "airunner",
                    "permission": [],
                    "root": "airunner",
                    "parent": None,
                }
            ],
        }
    )


def handle_openai_chat_completions(
    handler: Any,
    data: dict[str, Any],
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle OpenAI /v1/chat/completions requests."""
    success, error_msg = handler._ensure_llm_model_loaded()
    if not success:
        _send_model_unavailable(handler, error_msg)
        return
    messages = data.get("messages", [])
    if not messages:
        _send_messages_required(handler)
        return
    prompt, system_prompt = extract_prompt_and_system(messages)
    tools = data.get("tools", [])
    model = data.get("model", "airunner")
    llm_request = _build_openai_request(handler, data, prompt, system_prompt, tools)
    request_id = str(uuid.uuid4())
    if data.get("stream", False):
        handle_openai_chat_stream(
            handler,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
            tools=tools,
        )
        return
    handle_openai_chat_non_stream(
        handler,
        prompt,
        model,
        llm_request,
        request_id,
        get_api=get_api,
        tools=tools,
    )


def handle_openai_chat_stream(
    handler: Any,
    prompt: str,
    model: str,
    llm_request: Any,
    request_id: str,
    *,
    get_api: Callable[..., Any],
    tools: list[dict[str, Any]] | None = None,
) -> None:
    """Handle streaming OpenAI chat completions."""
    handler._set_headers(200, content_type="text/event-stream")
    complete_event = threading.Event()
    accumulated_response: list[str] = []
    api = get_api()
    if api is None:
        _write_sse(handler, {"error": {"message": "API not initialized"}})
        return
    callback = _stream_callback(
        handler,
        request_id,
        model,
        tools,
        accumulated_response,
        complete_event,
    )
    try:
        _dispatch_request(api, prompt, llm_request, request_id, callback)
        if not complete_event.wait(timeout=300):
            _write_sse(handler, {"error": {"message": "Request timeout"}})
    except Exception as error:
        _send_stream_exception(handler, error)
    handler.close_connection = True


def handle_openai_chat_non_stream(
    handler: Any,
    prompt: str,
    model: str,
    llm_request: Any,
    request_id: str,
    *,
    get_api: Callable[..., Any],
    tools: list[dict[str, Any]] | None = None,
) -> None:
    """Handle non-streaming OpenAI chat completions."""
    complete_event = threading.Event()
    complete_message: list[str] = []
    api = get_api()
    if api is None:
        _send_internal_error(handler, "API not initialized")
        return
    callback = _collect_callback(complete_message, complete_event)
    try:
        _dispatch_request(api, prompt, llm_request, request_id, callback)
        if complete_event.wait(timeout=300):
            _send_openai_completion(
                handler,
                prompt,
                model,
                request_id,
                "".join(complete_message),
                tools,
            )
            return
        _send_timeout(handler)
    except Exception as error:
        _send_non_stream_exception(handler, error)


def _send_model_unavailable(handler: Any, error_msg: str) -> None:
    """Send the standard unavailable-model payload."""
    handler._send_json_response(
        {
            "error": {
                "message": error_msg,
                "type": "service_unavailable",
                "hint": (
                    "Start with --model flag or configure model in AIRunner GUI"
                ),
            }
        },
        status=503,
    )


def _send_messages_required(handler: Any) -> None:
    """Send the standard missing-messages payload."""
    handler._send_json_response(
        {"error": {"message": "messages is required", "type": "invalid_request_error"}},
        status=400,
    )


def _build_openai_request(
    handler: Any,
    data: dict[str, Any],
    prompt: str,
    system_prompt: str,
    tools: list[dict[str, Any]],
) -> Any:
    """Create the internal LLM request for one OpenAI chat completion."""
    handler.logger.info("[OpenAI API] Extracted prompt (len=%s)", len(prompt))
    if system_prompt:
        handler.logger.info(
            "[OpenAI API] System prompt received (len=%s)",
            len(system_prompt),
        )
    enhanced_prompt = enhance_system_prompt(system_prompt, tools)
    _log_tool_mode(handler, tools)
    return create_llm_request(
        temperature=data.get("temperature", 0.7),
        max_tokens=data.get("max_tokens", 2048),
        system_prompt=enhanced_prompt,
        has_tools=bool(tools),
    )


def _log_tool_mode(handler: Any, tools: list[dict[str, Any]]) -> None:
    """Log whether tools are enabled for the OpenAI-compatible request."""
    if tools:
        handler.logger.info("[OpenAI API] Tools provided, enabling tool categories")
        return
    handler.logger.info("[OpenAI API] No tools provided, disabling all tools")


def _dispatch_request(
    api: Any,
    prompt: str,
    llm_request: Any,
    request_id: str,
    callback: Callable[[dict[str, Any]], None],
) -> None:
    """Dispatch one LLM chat request through the service API."""
    api.llm.send_request(
        prompt=prompt,
        action=LLMActionType.CHAT,
        llm_request=llm_request,
        request_id=request_id,
        callback=callback,
    )


def _stream_callback(
    handler: Any,
    request_id: str,
    model: str,
    tools: list[dict[str, Any]] | None,
    accumulated_response: list[str],
    complete_event: threading.Event,
) -> Callable[[dict[str, Any]], None]:
    """Return the streaming callback for OpenAI-compatible responses."""
    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if response is None:
            return
        accumulated_response.append(response.message)
        if response.is_end_of_message:
            _finish_stream_response(
                handler,
                request_id,
                model,
                tools,
                accumulated_response,
            )
            complete_event.set()
            return
        _write_sse(handler, _content_chunk(model, request_id, response.message))

    return callback


def _finish_stream_response(
    handler: Any,
    request_id: str,
    model: str,
    tools: list[dict[str, Any]] | None,
    accumulated_response: list[str],
) -> None:
    """Write the terminal streaming chunk and DONE marker."""
    full_text = "".join(accumulated_response)
    _content, tool_calls = parse_tool_calls_from_response(full_text, tools)
    if tool_calls:
        _write_sse(handler, _tool_call_chunk(model, request_id, tool_calls))
    else:
        _write_sse(handler, _stop_chunk(model, request_id))
    handler.wfile.write(b"data: [DONE]\n\n")
    handler.wfile.flush()


def _content_chunk(model: str, request_id: str, message: str) -> dict[str, Any]:
    """Return one streaming content chunk payload."""
    return {
        "id": _chunk_id(request_id),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": message},
            "finish_reason": None,
        }],
    }


def _tool_call_chunk(
    model: str,
    request_id: str,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return one streaming tool-call chunk payload."""
    return {
        "id": _chunk_id(request_id),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"tool_calls": tool_calls},
            "finish_reason": "tool_calls",
        }],
    }


def _stop_chunk(model: str, request_id: str) -> dict[str, Any]:
    """Return one terminal stop chunk payload."""
    return {
        "id": _chunk_id(request_id),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop",
        }],
    }


def _chunk_id(request_id: str) -> str:
    """Return the OpenAI-style chunk id for one request."""
    return f"chatcmpl-{request_id[:8]}"


def _write_sse(handler: Any, payload: dict[str, Any]) -> None:
    """Write one SSE payload and flush the stream."""
    handler.wfile.write(f"data: {json.dumps(payload)}\n\n".encode("utf-8"))
    handler.wfile.flush()


def _send_stream_exception(handler: Any, error: Exception) -> None:
    """Log and send one streaming exception payload."""
    handler.logger.error("OpenAI chat stream error: %s", error, exc_info=True)
    _write_sse(handler, {"error": {"message": str(error)}})


def _collect_callback(
    complete_message: list[str],
    complete_event: threading.Event,
) -> Callable[[dict[str, Any]], None]:
    """Return the non-streaming callback that accumulates responses."""
    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if response is None:
            return
        complete_message.append(response.message)
        if response.is_end_of_message:
            complete_event.set()

    return callback


def _send_openai_completion(
    handler: Any,
    prompt: str,
    model: str,
    request_id: str,
    full_response: str,
    tools: list[dict[str, Any]] | None,
) -> None:
    """Send the final non-streaming OpenAI chat response."""
    content, tool_calls = parse_tool_calls_from_response(full_response, tools)
    handler._send_json_response(
        {
            "id": _chunk_id(request_id),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": _completion_message(full_response, content, tool_calls),
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }],
            "usage": build_usage(prompt, full_response),
        }
    )


def _completion_message(
    full_response: str,
    content: str | None,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the assistant message payload for a completion response."""
    message = {"role": "assistant", "content": full_response}
    if tool_calls:
        message["content"] = content
        message["tool_calls"] = tool_calls
    return message


def _send_timeout(handler: Any) -> None:
    """Send the standard timeout response."""
    handler._send_json_response(
        {"error": {"message": "Request timeout"}},
        status=504,
    )


def _send_internal_error(handler: Any, message: str) -> None:
    """Send the standard internal error response."""
    handler._send_json_response({"error": {"message": message}}, status=500)


def _send_non_stream_exception(handler: Any, error: Exception) -> None:
    """Log and send one non-streaming exception payload."""
    handler.logger.error("OpenAI chat error: %s", error, exc_info=True)
    _send_internal_error(handler, str(error))