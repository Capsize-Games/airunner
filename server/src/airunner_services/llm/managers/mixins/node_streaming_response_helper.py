"""Streaming-response helpers for node functions."""

from __future__ import annotations

from typing import Dict, Optional

from langchain_core.messages import AIMessage

from airunner_services.llm.managers.mixins.node_streaming_state import (
    StreamingState,
)
from airunner_services.llm.managers.mixins.node_streaming_thinking_helper import (
    NodeStreamingThinkingHelper,
)
from airunner_services.llm.utils.stream_debug import print_stream_debug
from airunner_services.llm_workflow_events import (
    resolve_llm_workflow_event_sink,
)

_STRIP_ASSISTANT_PREFIXES = ("assistant\n", "assistant:", "assistant ")


def _strip_leading_assistant_preamble(text: str) -> str:
    """Strip 'assistant' role label from the start of one text chunk."""
    normalized = text.lstrip()
    lowered = normalized.lower()
    for prefix in _STRIP_ASSISTANT_PREFIXES:
        if lowered.startswith(prefix):
            return normalized[len(prefix) :]
    if lowered in {"assistant", "assistant:"}:
        return ""
    return text


class NodeStreamingResponseHelper:
    """Handle streamed chunk parsing for workflow nodes."""

    def __init__(self, owner) -> None:
        """Store the owning workflow manager."""
        self._owner = owner
        self._thinking_helper = NodeStreamingThinkingHelper(self)

    def generate_streaming_response(
        self,
        formatted_prompt,
        generation_kwargs: Dict,
    ) -> Optional[AIMessage]:
        """Generate one streamed response with thinking suppression."""
        state = StreamingState()
        event_sink = resolve_llm_workflow_event_sink(self._owner)
        request_id = getattr(self._owner, "_current_request_id", None)
        requested_max_tokens = generation_kwargs.get("max_new_tokens")
        if requested_max_tokens is None:
            requested_max_tokens = generation_kwargs.get("max_tokens")
        original_max_tokens = None
        try:
            if requested_max_tokens is not None and hasattr(
                self._owner._chat_model,
                "max_tokens",
            ):
                original_max_tokens = getattr(
                    self._owner._chat_model,
                    "max_tokens",
                    None,
                )
                self._owner._chat_model.max_tokens = requested_max_tokens
            self._owner.logger.info(
                "[STREAM] Starting stream from chat_model type: %s",
                type(self._owner._chat_model).__name__,
            )
            for chunk in self._owner._chat_model.stream(
                formatted_prompt,
                **generation_kwargs,
            ):
                if self._owner._interrupted:
                    break
                self._process_chunk(state, chunk, request_id, event_sink)
            self._thinking_helper.finalize_reasoning_delta(
                state,
                request_id,
                event_sink,
            )
            if state.streamed_content or state.last_chunk_message:
                thinking_to_save = self._thinking_helper.thinking_to_save(
                    state
                )
                return self._owner._get_response_generation_helper().create_streamed_message(
                    state.streamed_content,
                    state.last_chunk_message,
                    state.collected_tool_calls,
                    thinking_to_save,
                )
            self._owner.logger.error(
                "No generation chunks were returned; emitting empty AIMessage"
            )
            if self._owner._token_callback:
                try:
                    self._owner._token_callback("[generation stalled]")
                except Exception as callback_error:
                    self._owner.logger.error(
                        "Token callback failed while reporting stalled generation: %s",
                        callback_error,
                        exc_info=True,
                    )
            return AIMessage(
                content="",
                additional_kwargs={"error": "no_generation_chunks"},
                tool_calls=[],
            )
        except Exception as exc:
            self._owner.logger.error(
                "Error during streamed model call: %s",
                exc,
                exc_info=True,
            )
        finally:
            if original_max_tokens is not None:
                self._owner._chat_model.max_tokens = original_max_tokens
        return None

    def _process_chunk(
        self,
        state: StreamingState,
        chunk,
        request_id: Optional[str],
        event_sink,
    ) -> None:
        """Process one streamed chunk from the chat model."""
        chunk_message = getattr(chunk, "message", chunk)
        text = getattr(chunk_message, "content", "") or ""
        additional_kwargs = (
            getattr(chunk_message, "additional_kwargs", {}) or {}
        )
        reasoning_delta = additional_kwargs.get(
            "thinking_content"
        ) or additional_kwargs.get("reasoning_content")
        chunk_tool_calls = getattr(chunk_message, "tool_calls", None)
        print_stream_debug(
            "node_functions.chunk",
            request_id=request_id,
            content=text,
            reasoning_content=reasoning_delta,
            tool_calls=chunk_tool_calls,
            in_thinking_block=state.in_thinking_block,
        )
        state.last_chunk_message = chunk_message
        if chunk_tool_calls:
            state.collected_tool_calls.extend(chunk_tool_calls)
        if not text and not chunk_tool_calls and not reasoning_delta:
            return
        if self._thinking_helper.handle_reasoning_delta(
            state,
            request_id,
            event_sink,
            reasoning_delta,
            text,
        ):
            return
        if self._thinking_helper.handle_thinking_open(
            state,
            request_id,
            event_sink,
            text,
        ):
            return
        if state.in_thinking_block:
            self._thinking_helper.handle_thinking_block(
                state,
                request_id,
                event_sink,
                text,
            )
            return
        text_to_stream = self._filter_tool_markup(state, text)
        if text_to_stream:
            self._store_visible_text(state, request_id, text_to_stream)

    def _filter_tool_markup(self, state: StreamingState, text: str) -> str:
        """Return the text chunk as-is — tool call markup is preserved for visibility."""
        return text

    def _store_visible_text(
        self,
        state: StreamingState,
        request_id: Optional[str],
        text_to_stream: str,
        *,
        forward_to_callback: bool = True,
    ) -> None:
        """Persist one visible chunk and optionally forward it."""
        if not state.has_streamed_content:
            text_to_stream = _strip_leading_assistant_preamble(text_to_stream)
        if not text_to_stream:
            return
        state.streamed_content.append(text_to_stream)
        state.has_streamed_content = True
        if not forward_to_callback or not self._owner._token_callback:
            return
        print_stream_debug(
            "node_functions.visible",
            request_id=request_id,
            content=text_to_stream,
        )
        try:
            self._owner._token_callback(text_to_stream)
        except Exception as callback_error:
            self._owner.logger.error(
                "Token callback failed: %s",
                callback_error,
                exc_info=True,
            )
