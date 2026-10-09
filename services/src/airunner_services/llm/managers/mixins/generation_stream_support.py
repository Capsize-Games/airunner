"""Publication-gated generation stream helpers (S12).

Visible assistant text is buffered whole and reviewed with
:func:`airunner_services.content_safety_gate.evaluate_publication_fields`
before any stream signal carries it. Thinking/status events still flow
separately through :func:`create_thinking_callback` while text is held.
When the complete output is allowed it is flushed in order followed by
the end-of-message marker; when denied, only the generic denial final
message is published, which is distinct from model-failure text.
Cancellation drops buffered text instead of publishing it.
"""

from __future__ import annotations

from typing import Any, List, Optional

from airunner_common.llm_response import LLMResponse
from airunner_services.content_safety_gate import (
    GENERIC_PUBLICATION_DENIAL_MESSAGE,
    evaluate_publication_fields,
)
from airunner_services.llm.managers.mixins.generation_response_support import (
    executed_tools_from_workflow,
    extract_final_response,
    extract_final_tool_calls,
    extract_usage_tokens,
    fallback_response_for_empty_result,
    handle_generation_error,
    handle_interrupted_generation,
)
from airunner_services.llm.managers.mixins.generation_signal_support import (
    _is_assistant_preamble_only,
    _strip_leading_assistant_preamble,
    create_thinking_callback,
    current_assistant_turn_index,
    emit_visible_response as _emit_visible_response_ungated,
    send_end_of_message as _send_end_of_message_ungated,
)


def create_streaming_callback(
    owner,
    llm_request: Optional[Any],
    complete_response: List[str],
    sequence_counter: List[int],
):
    """Buffer streaming tokens without publishing visible text."""

    def handle_streaming_token(token_text: str) -> None:
        """Accumulate one token for whole-output review at publish."""
        if getattr(owner, "_interrupted", False):
            return
        token_text = _strip_leading_assistant_preamble(
            complete_response[0],
            token_text,
        )
        if not token_text:
            return
        complete_response[0] += token_text

    _reset_publication_state(owner)
    return handle_streaming_token


def emit_visible_response(
    owner,
    llm_request: Optional[Any],
    message: str,
    complete_response: List[str],
    sequence_counter: List[int],
) -> None:
    """Emit one visible chunk only after it passes the publication gate."""
    if _is_assistant_preamble_only(complete_response[0]):
        complete_response[0] = ""
    if not message or complete_response[0]:
        return
    if getattr(owner, "_interrupted", False):
        return
    result = evaluate_publication_fields({"message": message})
    if result.allowed:
        owner._publication_reviewed_text = message
        owner._publication_flushed = True
        _emit_visible_response_ungated(
            owner,
            llm_request,
            message,
            complete_response,
            sequence_counter,
        )
        return
    owner._publication_denied = True
    complete_response[0] = GENERIC_PUBLICATION_DENIAL_MESSAGE


def send_end_of_message(
    owner,
    llm_request: Optional[Any],
    sequence_counter: List[int],
    executed_tools: list[str],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
    final_visible_message: Optional[str] = None,
    tool_calls: Optional[list] = None,
) -> None:
    """Publish the end marker after the publication gate allows the text."""
    if getattr(owner, "_interrupted", False):
        _send_end_of_message_ungated(
            owner,
            llm_request,
            sequence_counter,
            executed_tools,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            None,
            tool_calls,
        )
        return
    text = final_visible_message or ""
    denied = bool(getattr(owner, "_publication_denied", False))
    if (
        not denied
        and text
        and text != getattr(owner, "_publication_reviewed_text", None)
    ):
        denied = not evaluate_publication_fields({"message": text}).allowed
    if denied:
        owner._publication_denied = True
        _send_end_of_message_ungated(
            owner,
            llm_request,
            sequence_counter,
            executed_tools,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            GENERIC_PUBLICATION_DENIAL_MESSAGE,
            tool_calls,
        )
        return
    if text and not getattr(owner, "_publication_flushed", False):
        _emit_allowed_visible_text(owner, llm_request, text, sequence_counter)
    _send_end_of_message_ungated(
        owner,
        llm_request,
        sequence_counter,
        executed_tools,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        final_visible_message,
        tool_calls,
    )


def _reset_publication_state(owner) -> None:
    """Clear per-generation publication review markers."""
    owner._publication_denied = False
    owner._publication_flushed = False
    owner._publication_reviewed_text = None


def _emit_allowed_visible_text(
    owner,
    llm_request: Optional[Any],
    text: str,
    sequence_counter: List[int],
) -> None:
    """Emit the reviewed buffered text as one ordered visible chunk."""
    sequence_counter[0] += 1
    owner.api.llm.send_llm_text_streamed_signal(
        LLMResponse(
            node_id=llm_request.node_id if llm_request else None,
            message=text,
            is_end_of_message=False,
            is_first_message=(sequence_counter[0] == 1),
            sequence_number=sequence_counter[0],
            request_id=getattr(owner, "_current_request_id", None),
            message_type="assistant",
            turn_index=current_assistant_turn_index(owner),
        )
    )


__all__ = [
    "create_streaming_callback",
    "create_thinking_callback",
    "emit_visible_response",
    "executed_tools_from_workflow",
    "extract_final_response",
    "extract_final_tool_calls",
    "extract_usage_tokens",
    "fallback_response_for_empty_result",
    "handle_generation_error",
    "handle_interrupted_generation",
    "send_end_of_message",
]
