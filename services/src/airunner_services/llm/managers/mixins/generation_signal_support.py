"""Signal-emission helpers for generation."""

from __future__ import annotations

from typing import Any, List, Optional

from airunner_services.llm.llm_response import LLMResponse
from airunner_services.llm.stream_text import prepare_stream_chunk


def current_assistant_turn_index(owner) -> int:
    """Return the current workflow assistant-turn index."""
    workflow_manager = getattr(owner, "_workflow_manager", None)
    turn_index = getattr(workflow_manager, "_assistant_turn_index", 0)
    return int(turn_index or 0)


def emit_visible_response(
    owner,
    llm_request: Optional[Any],
    message: str,
    complete_response: List[str],
    sequence_counter: List[int],
) -> None:
    """Emit one visible response chunk when streaming produced none."""
    if not message or complete_response[0]:
        return
    complete_response[0] = message
    sequence_counter[0] += 1
    owner.api.llm.send_llm_text_streamed_signal(
        LLMResponse(
            node_id=llm_request.node_id if llm_request else None,
            message=message,
            is_end_of_message=False,
            is_first_message=(sequence_counter[0] == 1),
            sequence_number=sequence_counter[0],
            request_id=getattr(owner, "_current_request_id", None),
            message_type="assistant",
            turn_index=current_assistant_turn_index(owner),
        )
    )


def create_streaming_callback(
    owner,
    llm_request: Optional[Any],
    complete_response: List[str],
    sequence_counter: List[int],
):
    """Create the callback that forwards streaming assistant tokens."""

    def handle_streaming_token(token_text: str) -> None:
        """Forward streaming tokens to the GUI and accumulate response."""
        if not token_text:
            return
        token_text = prepare_stream_chunk(complete_response[0], token_text)
        if not token_text:
            return
        complete_response[0] += token_text
        sequence_counter[0] += 1
        if not getattr(owner, "_current_request_id", None):
            owner.logger.warning(
                "[STREAM] Missing _current_request_id while streaming token"
            )
        owner.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                message=token_text,
                is_end_of_message=False,
                is_first_message=(sequence_counter[0] == 1),
                sequence_number=sequence_counter[0],
                request_id=getattr(owner, "_current_request_id", None),
                message_type="assistant",
                turn_index=current_assistant_turn_index(owner),
            )
        )

    return handle_streaming_token


def create_thinking_callback(
    owner,
    llm_request: Optional[Any],
    sequence_counter: List[int],
):
    """Create the callback that emits typed thinking chunks."""

    def handle_thinking_event(status: str, content: str) -> None:
        """Forward one thinking event to the streaming consumer."""
        sequence_counter[0] += 1
        owner.api.llm.send_llm_text_streamed_signal(
            LLMResponse(
                node_id=llm_request.node_id if llm_request else None,
                message=content or "",
                is_end_of_message=(status == "completed"),
                is_first_message=(status == "started"),
                sequence_number=sequence_counter[0],
                request_id=getattr(owner, "_current_request_id", None),
                message_type="thinking",
                turn_index=current_assistant_turn_index(owner),
            )
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
) -> None:
    """Emit the end-of-message chunk for one assistant response."""
    sequence_counter[0] += 1
    if not getattr(owner, "_current_request_id", None):
        owner.logger.warning(
            "[STREAM] Missing _current_request_id when sending end-of-message"
        )
    owner.api.llm.send_llm_text_streamed_signal(
        LLMResponse(
            node_id=llm_request.node_id if llm_request else None,
            is_end_of_message=True,
            sequence_number=sequence_counter[0],
            request_id=getattr(owner, "_current_request_id", None),
            tools=executed_tools,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            message_type="assistant",
            turn_index=current_assistant_turn_index(owner),
        )
    )