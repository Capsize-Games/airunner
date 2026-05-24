"""Service-owned mixin for daemon-backed LLM stream translation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from airunner_services.llm.llm_response import LLMResponse
from airunner_services.llm.stream_text import (
    append_stream_text,
    prepare_stream_chunk,
)
from airunner_services.llm.thinking_parser import (
    detect_thinking_close_tag,
    detect_thinking_open_tag,
    strip_thinking_tags,
)


@dataclass
class _DaemonStreamState:
    """Track one daemon-backed stream while it is translated to UI events."""

    in_thinking_block: bool = False
    thinking_tag_format: str = ""
    thinking_content: list[str] = field(default_factory=list)
    visible_sequence_number: int = 0
    visible_text: str = ""


class LLMDaemonStreamMixin:
    """Translate daemon NDJSON chunks into the local LLM response model."""

    def _stream_daemon_request(
        self,
        client,
        prompt: str,
        llm_request,
        action: object,
        request_id: str,
        search_hints: Optional[dict],
        conversation_id: Optional[int],
        node_id: Optional[str],
    ) -> None:
        """Emit streamed LLM responses received from the daemon client."""
        state = _DaemonStreamState()
        try:
            for chunk in client.stream_llm_request(
                prompt,
                llm_request,
                action,
                request_id,
                search_hints=search_hints,
                conversation_id=conversation_id,
                node_id=node_id,
            ):
                if chunk.get("keepalive"):
                    continue
                self._forward_daemon_chunk(
                    chunk,
                    state=state,
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
        except RuntimeError as exc:
            self.send_llm_text_streamed_signal(
                LLMResponse(
                    message=f"Error invoking LLM: {exc}",
                    is_first_message=True,
                    is_end_of_message=True,
                    action=action,
                    node_id=node_id,
                    request_id=request_id,
                    is_system_message=True,
                )
            )

    def _forward_daemon_chunk(
        self,
        chunk: dict,
        *,
        state: _DaemonStreamState,
        request_id: str,
        action: object,
        node_id: Optional[str],
    ) -> None:
        """Translate one daemon NDJSON chunk into visible response events."""
        if bool(chunk.get("error", False)):
            self.send_llm_text_streamed_signal(
                self._build_visible_daemon_response(
                    chunk,
                    state=state,
                    message=chunk.get("message", "") or "",
                    is_end_of_message=bool(
                        chunk.get("is_end_of_message", False)
                    ),
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
            )
            return

        visible_parts = self._extract_visible_daemon_text(
            chunk.get("message", "") or "",
            state,
            request_id=request_id,
        )
        if bool(chunk.get("is_end_of_message", False)):
            self._finish_daemon_thinking(state, request_id=request_id)

        if visible_parts:
            self._emit_visible_daemon_parts(
                visible_parts,
                chunk=chunk,
                state=state,
                request_id=request_id,
                action=action,
                node_id=node_id,
            )
            return

        if state.visible_sequence_number > 0 and bool(
            chunk.get("is_end_of_message", False)
        ):
            self.send_llm_text_streamed_signal(
                self._build_visible_daemon_response(
                    chunk,
                    state=state,
                    message="",
                    is_end_of_message=True,
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
            )

    def _emit_visible_daemon_parts(
        self,
        visible_parts: List[str],
        *,
        chunk: dict,
        state: _DaemonStreamState,
        request_id: str,
        action: object,
        node_id: Optional[str],
    ) -> None:
        """Emit one or more visible response chunks for the GUI."""
        last_index = len(visible_parts) - 1
        chunk_done = bool(chunk.get("is_end_of_message", False))
        for index, part in enumerate(visible_parts):
            cleaned_part = strip_thinking_tags(part)
            if not cleaned_part:
                continue
            normalized_part = prepare_stream_chunk(
                state.visible_text,
                cleaned_part,
            )
            if not normalized_part:
                continue
            state.visible_text = append_stream_text(
                state.visible_text,
                cleaned_part,
            )
            self.send_llm_text_streamed_signal(
                self._build_visible_daemon_response(
                    chunk,
                    state=state,
                    message=normalized_part,
                    is_end_of_message=chunk_done and index == last_index,
                    request_id=request_id,
                    action=action,
                    node_id=node_id,
                )
            )

    def _extract_visible_daemon_text(
        self,
        message: str,
        state: _DaemonStreamState,
        *,
        request_id: str,
    ) -> List[str]:
        """Split one daemon chunk into visible text and thinking updates."""
        visible_parts: List[str] = []
        remaining = message
        while remaining:
            if state.in_thinking_block:
                found_close, before_close, after_close = (
                    detect_thinking_close_tag(
                        remaining,
                        state.thinking_tag_format,
                    )
                )
                if found_close:
                    self._append_daemon_thinking(
                        state,
                        before_close,
                        request_id=request_id,
                    )
                    self._finish_daemon_thinking(
                        state,
                        request_id=request_id,
                    )
                    remaining = after_close
                    continue
                self._append_daemon_thinking(
                    state,
                    remaining,
                    request_id=request_id,
                )
                break

            found_open, tag_format, before_open, after_open = (
                detect_thinking_open_tag(remaining)
            )
            if not found_open:
                visible_parts.append(remaining)
                break
            if before_open:
                visible_parts.append(before_open)
            self._start_daemon_thinking(
                state,
                tag_format,
                request_id=request_id,
            )
            remaining = after_open
        return visible_parts

    def _start_daemon_thinking(
        self,
        state: _DaemonStreamState,
        tag_format: str,
        *,
        request_id: str,
    ) -> None:
        """Mark one daemon stream as being inside a thinking block."""
        state.in_thinking_block = True
        state.thinking_tag_format = tag_format
        state.thinking_content = []
        self.send_llm_thinking_signal("started", "", request_id)

    def _append_daemon_thinking(
        self,
        state: _DaemonStreamState,
        content: str,
        *,
        request_id: str,
    ) -> None:
        """Accumulate one thinking fragment and mirror it to the UI."""
        if not content:
            return
        state.thinking_content.append(content)
        self.send_llm_thinking_signal("streaming", content, request_id)

    def _finish_daemon_thinking(
        self,
        state: _DaemonStreamState,
        *,
        request_id: str,
    ) -> None:
        """Complete one thinking block if the daemon stream is inside one."""
        if not state.in_thinking_block:
            return
        self.send_llm_thinking_signal(
            "completed",
            "".join(state.thinking_content),
            request_id,
        )
        state.in_thinking_block = False
        state.thinking_tag_format = ""
        state.thinking_content = []

    def _build_visible_daemon_response(
        self,
        chunk: dict,
        *,
        state: _DaemonStreamState,
        message: str,
        is_end_of_message: bool,
        request_id: str,
        action: object,
        node_id: Optional[str],
    ) -> LLMResponse:
        """Build one GUI-visible response from a daemon NDJSON chunk."""
        state.visible_sequence_number += 1
        response = self._response_from_daemon_chunk(
            chunk,
            request_id=request_id,
            action=action,
            node_id=node_id,
        )
        response.message = message
        response.is_first_message = state.visible_sequence_number == 1
        response.is_end_of_message = is_end_of_message
        response.sequence_number = state.visible_sequence_number
        return response

    @staticmethod
    def _response_from_daemon_chunk(
        chunk: dict,
        *,
        request_id: str,
        action: object,
        node_id: Optional[str],
    ) -> LLMResponse:
        """Convert one daemon NDJSON chunk into the local response model."""
        response = LLMResponse(
            message=chunk.get("message", "") or "",
            is_first_message=bool(chunk.get("is_first_message", False)),
            is_end_of_message=bool(chunk.get("is_end_of_message", False)),
            action=action,
            node_id=node_id,
            sequence_number=int(chunk.get("sequence_number", 0) or 0),
            request_id=request_id,
            tools=chunk.get("tools") or chunk.get("tool_calls"),
            is_system_message=bool(chunk.get("error", False)),
        )
        usage = chunk.get("usage") or {}
        response.prompt_tokens = usage.get("prompt_tokens")
        response.completion_tokens = usage.get("completion_tokens")
        response.total_tokens = usage.get("total_tokens")
        return response