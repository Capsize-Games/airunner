"""Shared helpers for legacy LLM compatibility routes."""

from typing import Any, Callable, Dict, Optional

from airunner_common.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest

from .legacy_contracts import LegacyLLMGenerateRequest
from .legacy_sampling_bounds import (
    is_int_range as _is_int_range,
    in_range as _in_range,
)


def parse_action(action_str: str) -> LLMActionType:
    """Parse the legacy string action into one LLM action enum."""
    try:
        return LLMActionType[action_str]
    except Exception:
        return LLMActionType.CHAT


def terminal_stream_message(response: Any) -> bool:
    """Return whether one callback should terminate the HTTP LLM stream."""
    if not bool(getattr(response, "is_end_of_message", False)):
        return False
    message_type = getattr(response, "message_type", None)
    if isinstance(message_type, str):
        normalized = message_type.strip().lower()
        if normalized in {"thinking", "tool_call", "tool_result", "tool_status"}:
            return False
    return True


def tool_status_stream_payload(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert one request-scoped tool status event into NDJSON payload."""
    tool_id = data.get("tool_id")
    tool_name = data.get("tool_name")
    query = data.get("query")
    status = data.get("status")
    if not all([tool_id, tool_name, query, status]):
        return None
    return {
        "message": data.get("details") or "",
        "is_first_message": False,
        "is_end_of_message": status == "completed",
        "done": False,
        "sequence_number": 0,
        "turn_index": 0,
        "message_type": "tool_status",
        "tool_status": status,
        "tool_id": tool_id,
        "tool_name": tool_name,
        "tool_arguments": data.get("tool_arguments"),
        "query": query,
        "details": data.get("details") or "",
        "metadata": data.get("metadata"),
        "conversation_id": data.get("conversation_id"),
        "request_id": data.get("request_id"),
        "timestamp": data.get("timestamp"),
        "error": False,
        "is_system_message": False,
    }


def thinking_stream_payload(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert one request-scoped thinking event into NDJSON payload."""
    status = data.get("status")
    request_id = data.get("request_id")
    if status not in {"started", "streaming", "completed"}:
        return None
    if not request_id:
        return None
    content = data.get("content") or ""
    return {
        "message": content,
        "thinking_content": content,
        "is_first_message": status == "started",
        "is_end_of_message": status == "completed",
        "done": False,
        "sequence_number": 0,
        "turn_index": 0,
        "message_type": "thinking",
        "request_id": request_id,
        "error": False,
        "is_system_message": False,
    }


def _normalize_legacy_field_aliases(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remap common legacy field names to their canonical equivalents."""
    if "max_tokens" in data and "max_new_tokens" not in data:
        data = {**data, "max_new_tokens": data.get("max_tokens")}
    if "provider" in data and "model_service" not in data:
        data = {**data, "model_service": data.get("provider")}
    return data


def _is_bool(value: Any) -> bool:
    """Return whether a value is a real bool."""
    return isinstance(value, bool)


def _is_str(value: Any) -> bool:
    """Return whether a value is a string."""
    return isinstance(value, str)


def _is_opt_bool(value: Any) -> bool:
    """Return whether a value is None or a real bool."""
    return value is None or isinstance(value, bool)


def _is_tool_categories(value: Any) -> bool:
    """Return whether a value is a valid tool-category selection."""
    if value is None:
        return True
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


_LLM_FIELD_CHECKS: Dict[str, Callable[[Any], bool]] = {
    "temperature": lambda v: _in_range(v, 0.0, 2.0),
    "max_new_tokens": lambda v: _is_int_range(v, 1, 32768),
    "top_p": lambda v: _in_range(v, 0.0, 1.0),
    "top_k": lambda v: _is_int_range(v, 1, 200),
    "repetition_penalty": lambda v: _in_range(v, 0.0, 2.0),
    "min_length": lambda v: _is_int_range(v, 0, 32768),
    "num_beams": lambda v: _is_int_range(v, 1, 8),
    "num_return_sequences": lambda v: _is_int_range(v, 1, 8),
    "no_repeat_ngram_size": lambda v: _is_int_range(v, 1, 10),
    "length_penalty": lambda v: _in_range(v, 0.0, 5.0),
    "do_sample": _is_bool,
    "early_stopping": _is_bool,
    "use_cache": _is_bool,
    "use_memory": _is_bool,
    "ephemeral": _is_bool,
    "ephemeral_conversation": _is_bool,
    "do_tts_reply": _is_bool,
    "include_mood": _is_opt_bool,
    "include_datetime": _is_opt_bool,
    "include_style": _is_opt_bool,
    "include_memory": _is_opt_bool,
    "include_ui_context": _is_opt_bool,
    "enable_thinking": _is_bool,
    "reasoning_effort": _is_str,
    "response_format": _is_str,
    "system_prompt": _is_str,
    "model": _is_str,
    "node_id": _is_str,
    "gguf_runtime_profile": _is_str,
    "tool_categories": _is_tool_categories,
}


def _populate_llm_fields(data: Dict[str, Any], llm_request: LLMRequest) -> None:
    """Copy allowlisted fields from data into the LLMRequest.

    Only the generation/toggle fields above are assignable, each with
    its own type/range check; anything else is ignored. In particular
    ``rag_files``/``images`` (server-side file reads), ``dtype``
    (model reload), ``model_service``/``api_model`` (remote backend
    selection), ``force_tool``, and ``role`` can no longer be injected
    through an ``extra="allow"`` legacy payload.
    """
    for key, value in data.items():
        check = _LLM_FIELD_CHECKS.get(key)
        if value is None or check is None:
            continue
        if not check(value):
            continue
        try:
            setattr(llm_request, key, value)
        except Exception:
            pass


def _apply_remote_provider_model_rules(llm_request: LLMRequest) -> None:
    """Apply model name swap rules for remote provider services."""
    model_service = getattr(llm_request, "model_service", None)
    if model_service not in ("openrouter", "ollama"):
        return
    api_model = getattr(llm_request, "api_model", None)
    if api_model is None and getattr(llm_request, "model", ""):
        llm_request.api_model = llm_request.model
        llm_request.model = ""


def build_llm_request(data: Dict[str, Any]) -> LLMRequest:
    """Build one normalized LLMRequest from the legacy request payload."""
    data = _normalize_legacy_field_aliases(data)
    llm_request = LLMRequest()
    _populate_llm_fields(data, llm_request)
    if data.get("tool_categories") is None and "tools" not in data:
        llm_request.tool_categories = None
    _apply_remote_provider_model_rules(llm_request)
    return llm_request


def send_legacy_llm_request(
    app,
    prompt: str,
    action: LLMActionType,
    llm_request: LLMRequest,
    body: LegacyLLMGenerateRequest,
    request_id: str,
    callback,
) -> None:
    """Send one legacy LLM request through the shared app LLM interface."""
    app.llm.send_request(
        prompt=prompt,
        action=action,
        llm_request=llm_request,
        do_tts_reply=body.do_tts_reply,
        request_id=request_id,
        callback=callback,
        search_hints=body.search_hints,
        conversation_id=body.conversation_id,
        node_id=body.node_id,
    )