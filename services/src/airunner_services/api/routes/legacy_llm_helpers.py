"""Shared helpers for legacy LLM compatibility routes."""

from typing import Any, Dict, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest

from .legacy_contracts import LegacyLLMGenerateRequest


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


def _populate_llm_fields(data: Dict[str, Any], llm_request: LLMRequest) -> None:
    """Copy known fields from data into the LLMRequest, skipping None values."""
    for key, value in data.items():
        if value is None or not hasattr(llm_request, key):
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