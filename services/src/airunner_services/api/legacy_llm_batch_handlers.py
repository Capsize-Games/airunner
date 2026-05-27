"""LLM batch handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import json
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest

from airunner_services.api.legacy_llm_request_handlers import (
    create_llm_request,
    extract_llm_request_data,
    parse_action_type,
)


def handle_llm_batch(
    handler: Any,
    data: dict[str, Any],
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle one batch LLM generation request."""
    prompts = data.get("prompts")
    if not prompts or not isinstance(prompts, list):
        handler._send_json_response(
            {"error": "Missing or invalid 'prompts' field"},
            status=400,
        )
        return

    system_prompt = data.get("system_prompt")
    action = parse_action_type(data.get("action", "CHAT"))
    is_async = data.get("async", False)
    llm_request_data = extract_llm_request_data(data)
    _map_batch_top_level_params(data, llm_request_data)
    llm_request = create_llm_request(handler, llm_request_data)
    if is_async:
        _send_async_batch_response(handler, len(prompts))
        return
    handle_llm_batch_sync(
        handler,
        prompts,
        system_prompt,
        action,
        llm_request,
        get_api=get_api,
    )


def _map_batch_top_level_params(
    data: dict[str, Any],
    llm_request_data: dict[str, Any],
) -> None:
    """Map supported batch top-level parameters into llm_request data."""
    param_mapping = {
        "temperature": "temperature",
        "max_tokens": "max_new_tokens",
        "top_p": "top_p",
        "top_k": "top_k",
        "repetition_penalty": "repetition_penalty",
        "use_memory": "use_memory",
        "tool_categories": "tool_categories",
    }
    excluded = {
        "prompts",
        "system_prompt",
        "action",
        "stream",
        "async",
        "llm_request",
    }
    for client_param, llm_param in param_mapping.items():
        if client_param in data and client_param not in excluded:
            llm_request_data[llm_param] = data[client_param]


def _send_async_batch_response(handler: Any, total: int) -> None:
    """Send the accepted response for one async batch request."""
    batch_id = str(uuid.uuid4())
    handler._set_headers(202)
    handler.wfile.write(
        json.dumps(
            {
                "batch_id": batch_id,
                "status": "processing",
                "total": total,
            }
        ).encode("utf-8")
    )


def handle_llm_batch_sync(
    handler: Any,
    prompts: list[str],
    system_prompt: Optional[str],
    action: LLMActionType,
    llm_request: LLMRequest,
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle one synchronous batch LLM request."""
    del system_prompt
    responses = _batch_results(
        handler,
        prompts,
        action,
        llm_request,
        get_api=get_api,
    )
    handler._send_json_response(
        {
            "responses": responses,
            "total": len(prompts),
            "successful": sum(1 for item in responses if item["success"]),
            "failed": sum(1 for item in responses if not item["success"]),
        }
    )


def _batch_results(
    handler: Any,
    prompts: list[str],
    action: LLMActionType,
    llm_request: LLMRequest,
    *,
    get_api: Callable[..., Any],
) -> list[dict[str, Any]]:
    """Process one batch request in parallel and return sorted results."""
    responses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                _process_single_prompt,
                handler,
                index,
                prompt,
                action,
                llm_request,
                get_api,
            ): index
            for index, prompt in enumerate(prompts)
        }
        for future in as_completed(futures):
            responses.append(_resolve_future(prompts, futures, future))
    responses.sort(key=lambda item: item["index"])
    return responses


def _resolve_future(
    prompts: list[str],
    futures: dict[Any, int],
    future: Any,
) -> dict[str, Any]:
    """Resolve one batch future into a normalized result payload."""
    try:
        return future.result()
    except Exception as error:
        index = futures[future]
        return {
            "index": index,
            "prompt": prompts[index],
            "text": "",
            "success": False,
            "error": str(error),
            "duration": 0.0,
        }


def _process_single_prompt(
    handler: Any,
    index: int,
    prompt: str,
    action: LLMActionType,
    llm_request: LLMRequest,
    get_api: Callable[..., Any],
) -> dict[str, Any]:
    """Process one prompt in a synchronous batch request."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    complete_message: list[str] = []
    complete_event = threading.Event()
    callback = _batch_collect_callback(complete_message, complete_event)
    get_api().llm.send_request(
        prompt=prompt,
        action=action,
        llm_request=llm_request,
        request_id=request_id,
        callback=callback,
    )
    text, success, error = _batch_completion(
        complete_message,
        complete_event,
        handler._timeout,
    )
    return {
        "index": index,
        "prompt": prompt,
        "text": text,
        "success": success,
        "error": error,
        "duration": time.time() - start_time,
    }


def _batch_collect_callback(
    complete_message: list[str],
    complete_event: threading.Event,
) -> Callable[[dict[str, Any]], None]:
    """Return the callback used for one batch prompt."""

    def callback(data: dict[str, Any]) -> None:
        response = data.get("response")
        if not response:
            return
        complete_message.append(response.message)
        if response.is_end_of_message:
            complete_event.set()

    return callback


def _batch_completion(
    complete_message: list[str],
    complete_event: threading.Event,
    timeout: float,
) -> tuple[str, bool, Optional[str]]:
    """Return the result tuple for one batch prompt."""
    if complete_event.wait(timeout=timeout):
        return "".join(complete_message), True, None
    return "", False, "Request timeout"