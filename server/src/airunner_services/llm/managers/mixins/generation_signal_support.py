"""Signal-emission helpers for generation."""

from __future__ import annotations

from typing import Any, List, Optional

from airunner_services.llm.llm_response import LLMResponse


def current_assistant_turn_index(owner) -> int:
    """Return the current workflow assistant-turn index."""
    workflow_manager = getattr(owner, "_workflow_manager", None)
    turn_index = getattr(workflow_manager, "_assistant_turn_index", 0)
    return int(turn_index or 0)


def _is_assistant_preamble_only(text: str) -> bool:
    """Return True when streamed visible text is only an assistant label."""
    return (text or "").strip().lower() in {"assistant", "assistant:"}


def _strip_leading_assistant_preamble(existing: str, text: str) -> str:
    """Drop one leading assistant label from the first streamed chunk."""
    if existing or not text:
        return text
    normalized = text.lstrip()
    lowered = normalized.lower()
    for prefix in ("assistant\n", "assistant:", "assistant "):
        if lowered.startswith(prefix):
            return normalized[len(prefix) :].lstrip()
    if _is_assistant_preamble_only(normalized):
        return ""
    return text


def _signal_mediator_fallback(response: LLMResponse) -> None:
    """Route one response through SignalMediator when direct signal is
    unavailable."""
    request_id = getattr(response, "request_id", None)
    if not request_id:
        return
    from airunner_services.utils.application.signal_mediator import (
        SignalMediator,
    )

    SignalMediator().emit_signal(
        None,
        {"response": response, "request_id": request_id},
    )


def _send_signal(owner, llm_request, message, **kwargs):
    """Emit a streamed signal if the owner supports it."""
    response = LLMResponse(
        node_id=llm_request.node_id if llm_request else None,
        message=message,
        request_id=getattr(owner, "_current_request_id", None),
        turn_index=current_assistant_turn_index(owner),
        **kwargs,
    )
    if hasattr(owner, "send_llm_text_streamed_signal"):
        owner.send_llm_text_streamed_signal(response)
        return
    _signal_mediator_fallback(response)


def emit_visible_response(
    owner,
    llm_request: Optional[Any],
    message: str,
    complete_response: List[str],
    sequence_counter: List[int],
) -> None:
    """Emit one visible response chunk when streaming produced none."""
    if _is_assistant_preamble_only(complete_response[0]):
        complete_response[0] = ""
    if not message or complete_response[0]:
        return
    complete_response[0] = message
    sequence_counter[0] += 1
    _send_signal(
        owner,
        llm_request,
        message,
        is_end_of_message=False,
        is_first_message=(sequence_counter[0] == 1),
        sequence_number=sequence_counter[0],
        message_type="assistant",
    )


def _handle_streaming_token(
    token_text: str,
    owner,
    llm_request: Optional[Any],
    complete_response: List[str],
    sequence_counter: List[int],
) -> None:
    """Forward streaming tokens to the GUI and accumulate response."""
    token_text = _strip_leading_assistant_preamble(
        complete_response[0], token_text
    )
    if not token_text:
        return
    complete_response[0] += token_text
    sequence_counter[0] += 1
    if not getattr(owner, "_current_request_id", None):
        owner.logger.warning("[STREAM] Missing _current_request_id")
    _emit_token_signal(owner, llm_request, token_text, sequence_counter)


def _emit_token_signal(owner, llm_request, token_text, sequence_counter):
    """Emit a streamed signal for one token chunk."""
    _send_signal(
        owner,
        llm_request,
        token_text,
        is_end_of_message=False,
        is_first_message=(sequence_counter[0] == 1),
        sequence_number=sequence_counter[0],
        message_type="assistant",
    )


def create_streaming_callback(
    owner,
    llm_request: Optional[Any],
    complete_response: List[str],
    sequence_counter: List[int],
):
    """Create the callback that forwards streaming assistant tokens."""
    return lambda token_text: _handle_streaming_token(
        token_text,
        owner,
        llm_request,
        complete_response,
        sequence_counter,
    )


def create_thinking_callback(
    owner,
    llm_request: Optional[Any],
    sequence_counter: List[int],
):
    """Create the callback that emits typed thinking chunks."""

    def handle_thinking_event(status: str, content: str) -> None:
        """Forward one thinking event to the streaming consumer."""
        sequence_counter[0] += 1
        _send_signal(
            owner,
            llm_request,
            content or "",
            is_end_of_message=False,
            is_first_message=(status == "started"),
            sequence_number=sequence_counter[0],
            message_type="thinking",
        )

    return handle_thinking_event


def send_end_of_message(
    owner,
    llm_request: Optional[Any],
    sequence_counter: List[int],
    executed_tools: list[str],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
    final_visible_message: Optional[str] = None,
) -> None:
    """Emit the end-of-message chunk for one assistant response."""
    sequence_counter[0] += 1
    if not getattr(owner, "_current_request_id", None):
        owner.logger.warning(
            "[STREAM] Missing _current_request_id when sending end-of-message"
        )
    _send_signal(
        owner,
        llm_request,
        "",
        is_end_of_message=True,
        sequence_number=sequence_counter[0],
        final_visible_message=final_visible_message,
        tools=executed_tools,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        message_type="assistant",
    )
