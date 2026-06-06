"""Static helper utilities extracted from LocalFallbackLLMClient."""

from __future__ import annotations

from typing import Any

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    StreamDelta,
)


def response_message(response: Any) -> str:
    """Read message text from a legacy response object."""
    return getattr(response, "message", "")


def is_complete(response: Any) -> bool:
    """Return True when a legacy response marks completion."""
    return bool(getattr(response, "is_end_of_message", False))


def response_metadata(response: Any) -> dict[str, Any]:
    """Collect optional usage data from a legacy response object."""
    metadata = {}
    for field in ("tools", "prompt_tokens", "completion_tokens"):
        value = getattr(response, field, None)
        if value is not None:
            metadata[field] = value
    total_tokens = getattr(response, "total_tokens", None)
    if total_tokens is not None:
        metadata["total_tokens"] = total_tokens
    message_type = getattr(response, "message_type", None)
    if message_type:
        metadata["message_type"] = message_type
    return metadata


def resolve_action() -> Any:
    """Resolve the legacy action enum lazily."""
    from airunner_services.contract_enums import LLMActionType

    return LLMActionType.CHAT


def timeout_response(request_id: str, message: str) -> Any:
    """Create a timeout failure envelope."""
    from airunner_services.ipc.messages import ResponseEnvelope

    return ResponseEnvelope(
        request_id=request_id,
        status=EnvelopeStatus.FAILED,
        error=ErrorEnvelope(
            code="llm_timeout",
            message=message,
            retryable=True,
        ),
    )


def failure_delta(request_id: str, message: str) -> StreamDelta:
    """Create a terminal error delta for streamed requests."""
    return StreamDelta(
        request_id=request_id,
        final=True,
        status=EnvelopeStatus.FAILED,
        metadata={"error": message},
    )
