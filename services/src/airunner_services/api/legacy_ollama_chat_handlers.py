"""Ollama chat handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Callable, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest


def handle_ollama_chat(
    handler: Any,
    data: dict[str, Any],
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle the Ollama /api/chat endpoint."""
    success, error_msg = handler._ensure_llm_model_loaded()
    if not success:
        handler._send_json_response(
            {
                "error": error_msg,
                "hint": "Start with --model flag or configure model in AIRunner GUI",
            },
            status=503,
        )
        return
    messages = data.get("messages", [])
    tools = data.get("tools", [])
    model = data.get("model", "airunner:latest")
    stream = data.get("stream", True)
    options = data.get("options", {})
    handler.logger.info(
        "[Ollama API] /api/chat request: model=%s, stream=%s, "
        "messages=%s, tools=%s tool(s)",
        model,
        stream,
        len(messages),
        len(tools),
    )
    if not messages:
        handler._send_json_response({"error": "messages is required"}, status=400)
        return
    system_prompt, prompt = _chat_prompt_parts(messages)
    handler.logger.info("[Ollama API] Extracted prompt (len=%s)", len(prompt))
    if system_prompt:
        handler.logger.info(
            "[Ollama API] System prompt received (len=%s)",
            len(system_prompt),
        )
    llm_request = _ollama_chat_request(options, system_prompt, tools)
    request_id = str(uuid.uuid4())
    if stream:
        handle_ollama_chat_stream(
            handler,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
            tools=tools,
        )
        return
    handle_ollama_chat_non_stream(
        handler,
        prompt,
        model,
        llm_request,
        request_id,
        get_api=get_api,
        tools=tools,
    )


def _chat_prompt_parts(messages: list[dict[str, Any]]) -> tuple[str, str]:
    """Return the system prompt and latest user prompt from chat history."""
    system_prompt = ""
    last_user_content = ""
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_prompt = content
        elif role == "user":
            last_user_content = content
    return system_prompt, last_user_content


def _ollama_chat_request(
    options: dict[str, Any],
    system_prompt: str,
    tools: list[dict[str, Any]],
) -> LLMRequest:
    """Build the LLMRequest used by Ollama chat endpoints."""
    llm_request = LLMRequest()
    llm_request.temperature = options.get("temperature", 0.7)
    llm_request.max_new_tokens = options.get("num_predict", 2048)
    if system_prompt:
        llm_request.system_prompt = system_prompt
    llm_request.use_memory = False
    if tools:
        llm_request.tools = tools
        llm_request.tool_categories = None
    else:
        llm_request.tool_categories = []
    return llm_request


def handle_ollama_chat_stream(
    handler: Any,
    prompt: str,
    model: str,
    llm_request: LLMRequest,
    request_id: str,
    *,
    get_api: Callable[..., Any],
    tools: Optional[list[dict[str, Any]]] = None,
) -> None:
    """Handle the streaming Ollama chat response."""
    del tools
    handler._set_headers(200, content_type="application/x-ndjson")
    complete_event = threading.Event()
    start_time = time.time()
    api = get_api()
    if not api:
        _write_ollama_chat_line(handler, {"error": "API not initialized"})
        return
    callback = _chat_stream_callback(
        handler,
        complete_event,
        start_time,
        model,
        prompt,
    )
    try:
        api.llm.send_request(
            prompt=prompt,
            action=LLMActionType.CHAT,
            llm_request=llm_request,
            request_id=request_id,
            callback=callback,
        )
        if not complete_event.wait(timeout=300):
            _write_ollama_chat_line(
                handler,
                _ollama_chat_error(model, {"role": "assistant", "content": ""}, "Request timeout"),
            )
    except Exception as error:
        handler.logger.error("Ollama chat error: %s", error, exc_info=True)
        _write_ollama_chat_line(
            handler,
            _ollama_chat_error(model, {"role": "assistant", "content": ""}, str(error)),
        )
    handler.close_connection = True


def _chat_stream_callback(
    handler: Any,
    complete_event: threading.Event,
    start_time: float,
    model: str,
    prompt: str,
) -> Callable[[dict[str, Any]], None]:
    """Return the streaming callback used by Ollama chat."""

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        message = {"role": "assistant", "content": response.message}
        if hasattr(response, "tool_calls") and response.tool_calls:
            message["tool_calls"] = response.tool_calls
            message["content"] = ""
        payload = {
            "model": model,
            "created_at": _created_at(),
            "message": message,
            "done": response.is_end_of_message,
        }
        if response.is_end_of_message:
            payload.update(_ollama_chat_timings(start_time, prompt, response.message, False))
            payload["done_reason"] = "stop"
            complete_event.set()
        _write_ollama_chat_line(handler, payload)

    return callback


def handle_ollama_chat_non_stream(
    handler: Any,
    prompt: str,
    model: str,
    llm_request: LLMRequest,
    request_id: str,
    *,
    get_api: Callable[..., Any],
    tools: Optional[list[dict[str, Any]]] = None,
) -> None:
    """Handle the non-streaming Ollama chat response."""
    del tools
    complete_event = threading.Event()
    complete_message: list[str] = []
    tool_calls_result: list[Any] = []
    start_time = time.time()
    api = get_api()
    if not api:
        handler._send_json_response({"error": "API not initialized"}, status=500)
        return
    callback = _chat_collect_callback(complete_message, tool_calls_result, complete_event)
    try:
        api.llm.send_request(
            prompt=prompt,
            action=LLMActionType.CHAT,
            llm_request=llm_request,
            request_id=request_id,
            callback=callback,
        )
        if not complete_event.wait(timeout=300):
            handler._send_json_response({"error": "Request timeout"}, status=504)
            return
    except Exception as error:
        handler.logger.error("Ollama chat error: %s", error, exc_info=True)
        handler._send_json_response({"error": str(error)}, status=500)
        return
    full_response = "".join(complete_message)
    message = {"role": "assistant", "content": full_response}
    if tool_calls_result:
        message["tool_calls"] = tool_calls_result
        message["content"] = ""
    handler._send_json_response(
        {
            "model": model,
            "created_at": _created_at(),
            "message": message,
            "done_reason": "stop",
            "done": True,
            **_ollama_chat_timings(start_time, prompt, full_response, True),
        }
    )


def _chat_collect_callback(
    complete_message: list[str],
    tool_calls_result: list[Any],
    complete_event: threading.Event,
) -> Callable[[dict[str, Any]], None]:
    """Return the collection callback used by Ollama chat."""

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        complete_message.append(response.message)
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls_result.extend(response.tool_calls)
        if response.is_end_of_message:
            complete_event.set()

    return callback


def _write_ollama_chat_line(handler: Any, payload: dict[str, Any]) -> None:
    """Write one NDJSON Ollama chat payload."""
    handler.wfile.write(json.dumps(payload).encode("utf-8") + b"\n")
    handler.wfile.flush()


def _ollama_chat_error(
    model: str,
    message: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    """Return one terminal Ollama chat error payload."""
    return {
        "model": model,
        "created_at": _created_at(),
        "message": message,
        "done": True,
        "error": error,
    }


def _created_at() -> str:
    """Return the formatted Ollama timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())


def _ollama_chat_timings(
    start_time: float,
    prompt: str,
    response_text: str,
    use_response_length: bool,
) -> dict[str, int]:
    """Return the common Ollama chat duration and token counters."""
    duration_ns = int((time.time() - start_time) * 1e9)
    eval_count = len(response_text) // 4 if use_response_length else 100
    return {
        "total_duration": duration_ns,
        "load_duration": 0,
        "prompt_eval_count": len(prompt) // 4,
        "prompt_eval_duration": duration_ns // 10,
        "eval_count": eval_count,
        "eval_duration": duration_ns,
    }