"""LLM request handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import uuid
from typing import Any, Callable

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest

from airunner_services.api.legacy_llm_response_handlers import (
    handle_llm_non_stream,
    handle_llm_stream,
)


def extract_llm_request_data(data: dict[str, Any]) -> dict[str, Any]:
    """Extract and normalize one llm_request payload."""
    llm_request_raw = data.get("llm_request", {})
    if isinstance(llm_request_raw, dict):
        return llm_request_raw
    return {}


def map_top_level_params(
    data: dict[str, Any],
    llm_request_data: dict[str, Any],
) -> None:
    """Map legacy top-level request fields into an LLMRequest dict."""
    param_mapping = {
        "temperature": "temperature",
        "max_tokens": "max_new_tokens",
        "top_p": "top_p",
        "top_k": "top_k",
        "repetition_penalty": "repetition_penalty",
        "use_memory": "use_memory",
        "tool_categories": "tool_categories",
        "use_airunner_tools": "tool_categories",
        "model": "model",
        "rag_files": "rag_files",
        "enable_emotions": "include_mood",
        "include_mood": "include_mood",
        "include_datetime": "include_datetime",
        "include_style": "include_style",
        "include_memory": "include_memory",
        "include_ui_context": "include_ui_context",
    }
    excluded = {
        "prompt",
        "system_prompt",
        "action",
        "stream",
        "llm_request",
    }
    for client_param, llm_param in param_mapping.items():
        if client_param not in data or client_param in excluded:
            continue
        if client_param == "use_airunner_tools":
            _map_use_airunner_tools(data[client_param], llm_request_data)
            continue
        llm_request_data[llm_param] = data[client_param]

    if "tool_categories" not in llm_request_data and "tools" not in data:
        llm_request_data["tool_categories"] = None


def _map_use_airunner_tools(
    value: Any,
    llm_request_data: dict[str, Any],
) -> None:
    """Map the legacy use_airunner_tools flag into tool_categories."""
    if value is True:
        llm_request_data["tool_categories"] = None
    elif value is False:
        llm_request_data["tool_categories"] = []
    else:
        llm_request_data["tool_categories"] = value


def parse_action_type(action_str: Any) -> LLMActionType:
    """Parse one action string into an LLMActionType."""
    try:
        if isinstance(action_str, str):
            return LLMActionType[action_str]
        return action_str
    except KeyError:
        return LLMActionType.CHAT


def create_llm_request(
    handler: Any,
    params: dict[str, Any],
) -> LLMRequest:
    """Create an LLMRequest from a parameter dictionary."""
    llm_request = LLMRequest()
    handler.logger.debug("Creating LLMRequest from params: %s", params)
    for key, value in params.items():
        if hasattr(llm_request, key):
            setattr(llm_request, key, value)
            handler.logger.debug("Set LLMRequest.%s = %s", key, value)
            continue
        handler.logger.warning(
            "Ignoring unknown LLMRequest parameter: %s=%s",
            key,
            value,
        )
    return llm_request


def handle_llm(
    handler: Any,
    data: dict[str, Any],
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle one native LLM request with optional streaming."""
    print("HANDLE LLM CALLED")
    print("data", data)
    success, error_msg = handler._ensure_llm_model_loaded()
    if not success:
        handler._send_json_response(
            {
                "error": "Model not available",
                "details": error_msg,
                "hint": (
                    "Start with --model flag or configure model in "
                    "AIRunner GUI"
                ),
            },
            status=503,
        )
        return

    prompt = data.get("prompt")
    if not prompt:
        handler._send_json_response(
            {"error": "Missing 'prompt' field"},
            status=400,
        )
        return

    system_prompt = data.get("system_prompt")
    action = parse_action_type(data.get("action", "CHAT"))
    stream = data.get("stream", True)
    llm_request_data = extract_llm_request_data(data)
    map_top_level_params(data, llm_request_data)
    llm_request = create_llm_request(handler, llm_request_data)
    if system_prompt:
        llm_request.system_prompt = system_prompt
    request_id = str(uuid.uuid4())
    if stream:
        handle_llm_stream(
            handler,
            prompt,
            action,
            llm_request,
            request_id,
            get_api=get_api,
            search_hints=data.get("search_hints"),
        )
        return
    handle_llm_non_stream(
        handler,
        prompt,
        action,
        llm_request,
        request_id,
        get_api=get_api,
        search_hints=data.get("search_hints"),
    )