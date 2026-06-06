"""Thinking-state helpers for streamed node responses."""

from __future__ import annotations

from typing import Optional

from airunner_services.llm.managers.mixins.node_streaming_state import (
    StreamingState,
)
from airunner_services.llm.thinking_parser import (
    detect_thinking_close_tag,
    detect_thinking_open_tag,
)
from airunner_services.llm.utils.stream_debug import print_stream_debug


class NodeStreamingThinkingHelper:
    """Handle reasoning and thinking-tag state during streaming."""

    def __init__(self, owner) -> None:
        """Store the streaming helper that owns visible-text forwarding."""
        self._owner = owner

    def handle_reasoning_delta(
        self,
        state: StreamingState,
        request_id: Optional[str],
        event_sink,
        reasoning_delta: Optional[str],
        text: str,
    ) -> bool:
        """Handle one reasoning delta and return whether to stop processing."""
        if not reasoning_delta:
            return False
        if not state.thinking_started:
            state.thinking_started = True
            state.using_reasoning_deltas = True
            self.emit_thinking_signal(request_id, event_sink, "started", "")
        state.thinking_content.append(reasoning_delta)
        self.emit_thinking_signal(
            request_id,
            event_sink,
            "streaming",
            reasoning_delta,
        )
        if not text:
            return True
        if state.using_reasoning_deltas:
            state.using_reasoning_deltas = False
            state.final_thinking_content = "".join(state.thinking_content)
            self.emit_thinking_signal(
                request_id,
                event_sink,
                "completed",
                state.final_thinking_content,
            )
            state.thinking_content = []
        return False

    def handle_thinking_open(
        self,
        state: StreamingState,
        request_id: Optional[str],
        event_sink,
        text: str,
    ) -> bool:
        """Handle one thinking open tag if present."""
        found_open, tag_format, before_open, after_think = (
            detect_thinking_open_tag(text)
        )
        if not found_open or state.thinking_started:
            return False
        state.in_thinking_block = True
        state.thinking_started = True
        state.thinking_tag_format = tag_format
        self.emit_thinking_signal(request_id, event_sink, "started", "")
        if before_open:
            self._owner._store_visible_text(
                state,
                request_id,
                before_open,
                forward_to_callback=True,
            )
        found_close, before_close, after_close = detect_thinking_close_tag(
            after_think,
            tag_format,
        )
        if found_close:
            self.finish_thinking_block(
                state,
                request_id,
                event_sink,
                before_close,
            )
            if after_close:
                self._owner._store_visible_text(
                    state,
                    request_id,
                    after_close,
                    forward_to_callback=True,
                )
            return True
        if after_think:
            state.thinking_content.append(after_think)
            self.emit_thinking_signal(
                request_id,
                event_sink,
                "streaming",
                after_think,
            )
        return True

    def handle_thinking_block(
        self,
        state: StreamingState,
        request_id: Optional[str],
        event_sink,
        text: str,
    ) -> None:
        """Handle one chunk while already inside a thinking block."""
        found_close, before_close, after_close = detect_thinking_close_tag(
            text,
            state.thinking_tag_format,
        )
        if found_close:
            self.finish_thinking_block(
                state,
                request_id,
                event_sink,
                before_close,
            )
            if after_close:
                self._owner._store_visible_text(
                    state,
                    request_id,
                    after_close,
                    forward_to_callback=True,
                )
            return
        self.emit_thinking_signal(request_id, event_sink, "streaming", text)
        state.thinking_content.append(text)

    def finish_thinking_block(
        self,
        state: StreamingState,
        request_id: Optional[str],
        event_sink,
        before_close: str,
    ) -> None:
        """Close one thinking block and emit its final content."""
        if before_close:
            state.thinking_content.append(before_close)
            self.emit_thinking_signal(
                request_id,
                event_sink,
                "streaming",
                before_close,
            )
        state.in_thinking_block = False
        state.final_thinking_content = "".join(state.thinking_content)
        self.emit_thinking_signal(
            request_id,
            event_sink,
            "completed",
            state.final_thinking_content,
        )
        state.thinking_content = []

    def emit_thinking_signal(
        self,
        request_id: Optional[str],
        event_sink,
        status: str,
        content: str,
    ) -> None:
        """Emit one request-scoped thinking update."""
        manager = self._owner._owner
        print_stream_debug(
            "node_functions.thinking",
            request_id=request_id,
            status=status,
            content=content,
        )
        event_sink.emit_thinking(
            {"status": status, "content": content, "request_id": request_id}
        )
        thinking_callback = getattr(manager, "_thinking_callback", None)
        if not callable(thinking_callback):
            return
        try:
            thinking_callback(status, content or "")
        except Exception as callback_error:
            manager.logger.error(
                "Thinking callback failed: %s",
                callback_error,
                exc_info=True,
            )

    def finalize_reasoning_delta(
        self,
        state: StreamingState,
        request_id: Optional[str],
        event_sink,
    ) -> None:
        """Emit any unfinished reasoning delta after streaming ends."""
        if not state.using_reasoning_deltas or not state.thinking_content:
            return
        state.final_thinking_content = "".join(state.thinking_content)
        self.emit_thinking_signal(
            request_id,
            event_sink,
            "completed",
            state.final_thinking_content,
        )

    @staticmethod
    def thinking_to_save(state: StreamingState) -> Optional[str]:
        """Return persisted thinking content for the final AI message."""
        if state.final_thinking_content:
            return state.final_thinking_content
        if state.thinking_content:
            return "".join(state.thinking_content)
        return None
