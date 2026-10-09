"""Runtime-delta to companion-event adaptation (B12).

Converts the existing ``StreamDelta`` sequence (the same one
``stream_runtime()`` in ``api/routes/llm_runtime.py`` yields) into
``CompanionStreamEvent`` values: text and tool calls pass through,
a FAILED delta becomes a terminal retryable error event, and a
cancelled turn gets a terminal CANCELLED event.
"""

from __future__ import annotations

from typing import Any, Dict

from airunner_services.ipc.messages import EnvelopeStatus

from .contracts import (
    ERROR_CANCELLED,
    ERROR_INFERENCE_UNAVAILABLE,
    CallChainId,
    CompanionErrorCode,
    CompanionStreamEvent,
)


def adapt_delta(
    call_chain_id: CallChainId, delta: Any
) -> CompanionStreamEvent:
    """Adapt one runtime ``StreamDelta`` to a turn event."""
    status = getattr(delta, "status", EnvelopeStatus.STREAM)
    sequence = int(getattr(delta, "sequence", 0))
    if status == EnvelopeStatus.FAILED:
        return failed_event(call_chain_id, sequence)
    payload: Dict[str, Any] = dict(getattr(delta, "delta", {}) or {})
    return CompanionStreamEvent(
        call_chain_id=call_chain_id,
        sequence=sequence,
        delta_text=str(payload.get("content", "")),
        tool_calls=list(payload.get("tool_calls") or []),
        final=bool(getattr(delta, "final", False)),
        status=status,
    )


def failed_event(
    call_chain_id: CallChainId, sequence: int
) -> CompanionStreamEvent:
    """Build the terminal event for a failed runtime delta."""
    return CompanionStreamEvent(
        call_chain_id=call_chain_id,
        sequence=sequence,
        final=True,
        status=EnvelopeStatus.FAILED,
        error=CompanionErrorCode(
            code=ERROR_INFERENCE_UNAVAILABLE,
            detail="local inference failed mid-stream",
            retryable=True,
        ),
    )


def cancelled_event(
    call_chain_id: CallChainId, sequence: int
) -> CompanionStreamEvent:
    """Build the terminal event for a cancelled turn."""
    return CompanionStreamEvent(
        call_chain_id=call_chain_id,
        sequence=sequence,
        final=True,
        status=EnvelopeStatus.CANCELLED,
        error=CompanionErrorCode(code=ERROR_CANCELLED),
    )


__all__ = [
    "adapt_delta",
    "cancelled_event",
    "failed_event",
]
