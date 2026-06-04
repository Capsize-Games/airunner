"""Ollama generation handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import json
import random
import threading
import time
import uuid
from typing import Any, Callable

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest


def handle_ollama_generate(
    handler: Any,
    data: dict[str, Any],
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle the Ollama /api/generate endpoint."""
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
    prompt = data.get("prompt", "")
    if not prompt:
        handler._send_json_response({"error": "prompt is required"}, status=400)
        return
    llm_request = _ollama_generate_request(data)
    request_id = str(uuid.uuid4())
    model = data.get("model", "airunner:latest")
    if data.get("stream", True):
        handle_ollama_generate_stream(
            handler,
            prompt,
            model,
            llm_request,
            request_id,
            get_api=get_api,
        )
        return
    handle_ollama_generate_non_stream(
        handler,
        prompt,
        model,
        llm_request,
        request_id,
        get_api=get_api,
    )


def _ollama_generate_request(data: dict[str, Any]) -> LLMRequest:
    """Build the LLMRequest used by Ollama generate endpoints."""
    llm_request = LLMRequest()
    options = data.get("options", {})
    llm_request.temperature = options.get("temperature", 0.7)
    llm_request.max_new_tokens = options.get("num_predict", 2048)
    system = data.get("system", "")
    if system:
        llm_request.system_prompt = system
    return llm_request


def handle_ollama_generate_stream(
    handler: Any,
    prompt: str,
    model: str,
    llm_request: LLMRequest,
    request_id: str,
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle the streaming Ollama generate response."""
    handler._set_headers(200, content_type="application/x-ndjson")
    complete_event = threading.Event()
    start_time = time.time()
    api = get_api()
    if not api:
        _write_ollama_ndjson(handler, {"error": "API not initialized"})
        return
    callback = _generate_stream_callback(
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
            _write_ollama_ndjson(handler, _ollama_generate_error(model, "Request timeout"))
    except Exception as error:
        handler.logger.error("Ollama generate error: %s", error, exc_info=True)
        _write_ollama_ndjson(handler, _ollama_generate_error(model, str(error)))
    handler.close_connection = True


def _generate_stream_callback(
    handler: Any,
    complete_event: threading.Event,
    start_time: float,
    model: str,
    prompt: str,
) -> Callable[[dict[str, Any]], None]:
    """Return the streaming callback for Ollama generate."""

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        payload = {
            "model": model,
            "created_at": _created_at(),
            "response": response.message,
            "done": response.is_end_of_message,
        }
        if response.is_end_of_message:
            payload.update(_ollama_timings(start_time, prompt, response.message, False))
            complete_event.set()
        _write_ollama_ndjson(handler, payload)

    return callback


def handle_ollama_generate_non_stream(
    handler: Any,
    prompt: str,
    model: str,
    llm_request: LLMRequest,
    request_id: str,
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle the non-streaming Ollama generate response."""
    complete_event = threading.Event()
    complete_message: list[str] = []
    start_time = time.time()
    api = get_api()
    if not api:
        handler._send_json_response({"error": "API not initialized"}, status=500)
        return
    callback = _collect_text_callback(complete_message, complete_event)
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
        handler.logger.error("Ollama generate error: %s", error, exc_info=True)
        handler._send_json_response({"error": str(error)}, status=500)
        return
    full_response = "".join(complete_message)
    handler._send_json_response(
        {
            "model": model,
            "created_at": _created_at(),
            "response": full_response,
            "done": True,
            **_ollama_timings(start_time, prompt, full_response, True),
        }
    )


def handle_ollama_pull(handler: Any, data: dict[str, Any]) -> None:
    """Handle the Ollama /api/pull endpoint."""
    model = data.get("model", "airunner:latest")
    responses = [
        {"status": "pulling manifest"},
        {"status": f"pulling {model}"},
        {"status": "verifying sha256 digest"},
        {"status": "writing manifest"},
        {"status": "success"},
    ]
    _send_stream_or_success(handler, data.get("stream", True), responses)


def handle_ollama_embed(handler: Any, data: dict[str, Any]) -> None:
    """Handle the Ollama /api/embed endpoint with placeholder embeddings."""
    input_text = data.get("input", data.get("prompt", ""))
    if isinstance(input_text, list):
        embeddings = [_embedding_vector() for _ in input_text]
    else:
        embeddings = [_embedding_vector()]
    handler._send_json_response(
        {
            "model": data.get("model", "airunner:latest"),
            "embeddings": embeddings,
            "total_duration": 1000000,
            "load_duration": 100000,
            "prompt_eval_count": len(str(input_text)) // 4,
        }
    )


def handle_ollama_copy(handler: Any, data: dict[str, Any]) -> None:
    """Handle the Ollama /api/copy endpoint."""
    del data
    handler._send_json_response({"status": "success"})


def handle_ollama_create(handler: Any, data: dict[str, Any]) -> None:
    """Handle the Ollama /api/create endpoint."""
    responses = [
        {"status": "reading model metadata"},
        {"status": "creating system layer"},
        {"status": "writing manifest"},
        {"status": "success"},
    ]
    _send_stream_or_success(handler, data.get("stream", True), responses)


def _send_stream_or_success(
    handler: Any,
    stream: bool,
    responses: list[dict[str, Any]],
) -> None:
    """Send either one streamed NDJSON sequence or one success object."""
    if not stream:
        handler._send_json_response({"status": "success"})
        return
    handler._set_headers(200, content_type="application/x-ndjson")
    for response in responses:
        _write_ollama_ndjson(handler, response)


def _embedding_vector() -> list[float]:
    """Return one placeholder embedding vector."""
    return [random.uniform(-1, 1) for _ in range(384)]


def _collect_text_callback(
    complete_message: list[str],
    complete_event: threading.Event,
) -> Callable[[dict[str, Any]], None]:
    """Return the callback used by Ollama generate collection."""

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        complete_message.append(response.message)
        if response.is_end_of_message:
            complete_event.set()

    return callback


def _write_ollama_ndjson(handler: Any, payload: dict[str, Any]) -> None:
    """Write one Ollama NDJSON payload."""
    handler.wfile.write(json.dumps(payload).encode("utf-8") + b"\n")
    handler.wfile.flush()


def _ollama_generate_error(model: str, message: str) -> dict[str, Any]:
    """Return one terminal Ollama generate error payload."""
    return {
        "model": model,
        "created_at": _created_at(),
        "response": "",
        "done": True,
        "error": message,
    }


def _created_at() -> str:
    """Return the formatted Ollama timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())


def _ollama_timings(
    start_time: float,
    prompt: str,
    response_text: str,
    use_response_length: bool,
) -> dict[str, int]:
    """Return the common Ollama duration and token counters."""
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