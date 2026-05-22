"""Streaming response helpers for node functions."""

import json
import os
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage

from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.components.llm.utils.stream_text import combine_stream_chunks
from airunner.components.llm.utils.thinking_parser import (
    detect_thinking_close_tag,
    detect_thinking_open_tag,
)
from airunner.enums import SignalCode


class StreamingResponseMixin:
    """Run the raw streaming loop and buffer visible output."""

    def _is_tool_call_json(self, text: str) -> bool:
        """Check whether text strongly resembles a tool-call JSON block."""
        stripped = text.strip()
        if not stripped.startswith("{"):
            return False

        if ('"name"' in stripped or '"tool"' in stripped) and (
            '"arguments"' in stripped or '"args"' in stripped
        ):
            return True
        if '"tool"' in stripped and any(
            key in stripped
            for key in (
                '"query"',
                '"prompt"',
                '"url"',
                '"path"',
                '"text"',
                '"content"',
            )
        ):
            return True
        if '"function"' in stripped and '"arguments"' in stripped:
            return True
        return False

    def _generate_streaming_response(
        self,
        formatted_prompt: Any,
        generation_kwargs: Dict[str, Any],
        thinking_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AIMessage]:
        """Generate a response using the raw streaming model path."""
        chat_model = getattr(self, "_chat_model", None)
        if chat_model is None:
            return None

        streamed_content: List[str] = []
        last_chunk_message: Optional[BaseMessage] = None
        collected_tool_calls: List = []
        in_thinking_block = False
        thinking_started = False
        thinking_tag_format = ""
        using_reasoning_deltas = False
        thinking_content: List[str] = []
        final_thinking_content = None
        tool_call_tag_buffer: List[str] = []
        in_tool_call_tag = False
        json_buffer: List[str] = []
        in_json_tool_call = False
        json_brace_depth = 0
        has_streamed_content = False

        emitter = getattr(self, "_signal_emitter", None)
        has_emitter = emitter is not None
        request_id = getattr(self, "_current_request_id", None)
        tool_choice = getattr(self, "_tool_choice", None)
        forced_tool_choice = (
            isinstance(tool_choice, dict)
            and isinstance(tool_choice.get("function"), dict)
            and bool(tool_choice["function"].get("name"))
        )
        hold_visible_output = bool(
            getattr(self, "_force_tool", None) or forced_tool_choice
        )
        pending_visible_chunks: List[str] = []
        headless_thinking_open = False
        emitted_tool_call_keys: set[str] = set()

        def emit_headless_phase_chunk(response: LLMResponse) -> None:
            """Route one typed phase chunk through the headless path."""
            if not is_headless or not has_emitter:
                return
            emitter.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                {
                    "response": response,
                    "request_id": request_id,
                },
            )

        def emit_headless_thinking_chunk(
            content: str,
            *,
            is_end: bool = False,
        ) -> None:
            """Emit one typed thinking chunk for daemon streaming."""
            nonlocal headless_thinking_open
            if not is_headless or not has_emitter:
                return
            if not headless_thinking_open and not content and not is_end:
                return
            emit_headless_phase_chunk(
                LLMResponse(
                    message="",
                    is_first_message=not headless_thinking_open,
                    is_end_of_message=is_end,
                    request_id=request_id,
                    message_type="thinking",
                    thinking_content=content,
                )
            )
            if not headless_thinking_open:
                headless_thinking_open = True
            if is_end:
                headless_thinking_open = False

        def emit_headless_tool_call_chunk(
            tool_call: Dict[str, Any],
        ) -> None:
            """Emit one typed tool-call chunk for daemon streaming."""
            if not is_headless or not has_emitter:
                return
            tool_name = str(tool_call.get("name") or "").strip()
            if not tool_name:
                return
            tool_args = tool_call.get("args") or tool_call.get("arguments")
            dedupe_key = json.dumps(
                {
                    "id": tool_call.get("id"),
                    "name": tool_name,
                    "arguments": tool_args,
                },
                sort_keys=True,
                default=str,
            )
            if dedupe_key in emitted_tool_call_keys:
                return
            emitted_tool_call_keys.add(dedupe_key)
            emit_headless_phase_chunk(
                LLMResponse(
                    message="",
                    is_first_message=True,
                    is_end_of_message=True,
                    request_id=request_id,
                    message_type="tool_call",
                    tool_name=tool_name,
                    tool_arguments=(
                        tool_args if isinstance(tool_args, dict) else None
                    ),
                    tool_status="completed",
                )
            )

        def emit_thinking_signal(status: str, content: str) -> None:
            """Emit one request-scoped thinking update to the GUI."""
            if not has_emitter:
                return
            emitter.emit_signal(
                SignalCode.LLM_THINKING_SIGNAL,
                {
                    "status": status,
                    "content": content,
                    "request_id": request_id,
                    "metadata": thinking_metadata,
                },
            )

        def forward_stream_text(text_to_stream: str) -> None:
            """Forward one raw chunk to the token callback."""
            if not self._token_callback or not text_to_stream:
                return
            try:
                self._token_callback(text_to_stream)
            except Exception as callback_error:
                self.logger.error(
                    "Token callback failed: %s",
                    callback_error,
                    exc_info=True,
                )

        def store_visible_text(
            text_to_stream: str,
            *,
            forward_to_callback: bool = True,
        ) -> None:
            """Persist one visible chunk and optionally forward it."""
            nonlocal has_streamed_content
            if not has_streamed_content:
                text_to_stream = text_to_stream.lstrip()
            if not text_to_stream:
                return

            streamed_content.append(text_to_stream)
            has_streamed_content = True
            if hold_visible_output:
                pending_visible_chunks.append(text_to_stream)
                return
            if forward_to_callback:
                forward_stream_text(text_to_stream)

        is_headless = os.environ.get("AIRUNNER_HEADLESS", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        suppress_thinking_blocks = bool(has_emitter) and not is_headless
        suppress_tool_call_markup = bool(has_emitter) and not is_headless

        try:
            self.logger.info(
                "[STREAM] Starting stream from chat_model type: %s",
                type(chat_model).__name__,
            )
            for chunk in chat_model.stream(
                formatted_prompt,
                **generation_kwargs,
            ):
                if getattr(self, "_interrupted", False):
                    break

                chunk_message = getattr(chunk, "message", chunk)
                text = getattr(chunk_message, "content", "") or ""
                additional_kwargs = (
                    getattr(chunk_message, "additional_kwargs", {}) or {}
                )
                reasoning_delta = (
                    additional_kwargs.get("thinking_content")
                    or additional_kwargs.get("reasoning_content")
                )

                last_chunk_message = chunk_message

                chunk_tool_calls = getattr(chunk_message, "tool_calls", None)
                if chunk_tool_calls:
                    collected_tool_calls.extend(chunk_tool_calls)
                    for tool_call in chunk_tool_calls:
                        if isinstance(tool_call, dict):
                            emit_headless_tool_call_chunk(tool_call)

                if not text and not chunk_tool_calls and not reasoning_delta:
                    continue

                if reasoning_delta:
                    if not thinking_started:
                        thinking_started = True
                        using_reasoning_deltas = True
                        emit_thinking_signal("started", "")

                    thinking_content.append(reasoning_delta)
                    emit_thinking_signal("streaming", reasoning_delta)
                    emit_headless_thinking_chunk(reasoning_delta)

                    if not text:
                        continue

                if using_reasoning_deltas and text:
                    using_reasoning_deltas = False
                    final_thinking_content = "".join(thinking_content)
                    emit_thinking_signal(
                        "completed",
                        final_thinking_content,
                    )
                    emit_headless_thinking_chunk("", is_end=True)
                    thinking_content = []

                found_open, tag_format, before_open, after_think = (
                    detect_thinking_open_tag(text)
                )
                if found_open and not thinking_started:
                    if not suppress_thinking_blocks:
                        forward_stream_text(text)
                    in_thinking_block = True
                    thinking_started = True
                    thinking_tag_format = tag_format
                    emit_thinking_signal("started", "")

                    if before_open:
                        store_visible_text(
                            before_open,
                            forward_to_callback=suppress_thinking_blocks,
                        )

                    found_close, before_close, after_close = (
                        detect_thinking_close_tag(after_think, tag_format)
                    )
                    if found_close:
                        if before_close:
                            thinking_content.append(before_close)
                            emit_thinking_signal(
                                "streaming",
                                before_close,
                            )
                            emit_headless_thinking_chunk(before_close)

                        in_thinking_block = False
                        final_thinking_content = "".join(thinking_content)
                        emit_thinking_signal(
                            "completed",
                            final_thinking_content,
                        )
                        emit_headless_thinking_chunk("", is_end=True)
                        thinking_content = []

                        if after_close:
                            store_visible_text(
                                after_close,
                                forward_to_callback=suppress_thinking_blocks,
                            )
                    elif after_think:
                        thinking_content.append(after_think)
                        emit_thinking_signal(
                            "streaming",
                            after_think,
                        )
                        emit_headless_thinking_chunk(after_think)
                    continue

                if in_thinking_block:
                    if not suppress_thinking_blocks:
                        forward_stream_text(text)

                    found_close, before_close, after_close = (
                        detect_thinking_close_tag(text, thinking_tag_format)
                    )
                    if found_close:
                        if before_close:
                            thinking_content.append(before_close)
                            emit_thinking_signal(
                                "streaming",
                                before_close,
                            )
                            emit_headless_thinking_chunk(before_close)

                        in_thinking_block = False
                        final_thinking_content = "".join(thinking_content)
                        emit_thinking_signal(
                            "completed",
                            final_thinking_content,
                        )
                        emit_headless_thinking_chunk("", is_end=True)
                        thinking_content = []

                        if after_close:
                            store_visible_text(
                                after_close,
                                forward_to_callback=suppress_thinking_blocks,
                            )
                    else:
                        emit_thinking_signal("streaming", text)
                        thinking_content.append(text)
                        emit_headless_thinking_chunk(text)
                    continue

                text_to_stream = text

                if suppress_tool_call_markup:
                    if not in_tool_call_tag and "<tool_call>" in text:
                        in_tool_call_tag = True
                        before_tag = text.split("<tool_call>", 1)[0]
                        if before_tag.strip():
                            text_to_stream = before_tag
                        else:
                            text_to_stream = ""
                        tool_call_tag_buffer.append(
                            text.split("<tool_call>", 1)[1]
                            if "<tool_call>" in text
                            else ""
                        )
                        continue

                    if in_tool_call_tag:
                        if "</tool_call>" in text:
                            before_close = text.split("</tool_call>", 1)[0]
                            tool_call_tag_buffer.append(before_close)
                            in_tool_call_tag = False
                            after_close = (
                                text.split("</tool_call>", 1)[1]
                                if "</tool_call>" in text
                                else ""
                            )
                            if after_close.strip():
                                text_to_stream = after_close
                            else:
                                text_to_stream = ""
                            tool_call_tag_buffer = []
                        else:
                            tool_call_tag_buffer.append(text)
                            text_to_stream = ""
                        if not text_to_stream:
                            continue

                    if not in_json_tool_call and "{" in text:
                        remaining = text[text.index("{"):]
                        if self._is_tool_call_json(remaining):
                            in_json_tool_call = True
                            before_json = text[:text.index("{")]
                            if before_json.strip():
                                text_to_stream = before_json
                            else:
                                text_to_stream = ""
                            json_buffer.append(text[text.index("{"):])
                            json_brace_depth = (
                                text.count("{") - text.count("}")
                            )

                    if in_json_tool_call and text_to_stream == text:
                        json_buffer.append(text)
                        json_brace_depth += (
                            text.count("{") - text.count("}")
                        )
                        text_to_stream = ""

                        if json_brace_depth <= 0:
                            in_json_tool_call = False
                            buffered = "".join(json_buffer)
                            if "}" in buffered:
                                last_brace = buffered.rfind("}")
                                after_json = buffered[last_brace + 1:]
                                if after_json.strip():
                                    text_to_stream = after_json
                            json_buffer = []
                            json_brace_depth = 0

                store_visible_text(text_to_stream)

            if using_reasoning_deltas and thinking_content:
                final_thinking_content = "".join(thinking_content)
                emit_thinking_signal(
                    "completed",
                    final_thinking_content,
                )
                emit_headless_thinking_chunk("", is_end=True)

            if hold_visible_output and not collected_tool_calls:
                combined_visible = combine_stream_chunks(pending_visible_chunks)
                if combined_visible:
                    forward_stream_text(combined_visible)
            elif hold_visible_output and collected_tool_calls:
                streamed_content = []

            if streamed_content or last_chunk_message:
                thinking_to_save = final_thinking_content or (
                    "".join(thinking_content) if thinking_content else None
                )
                return self._create_streamed_message(
                    streamed_content,
                    last_chunk_message,
                    collected_tool_calls,
                    thinking_to_save,
                    thinking_metadata,
                )

            self.logger.error(
                "No generation chunks were returned; emitting empty AIMessage"
            )
            if self._token_callback:
                try:
                    self._token_callback("[generation stalled]")
                except Exception as callback_error:
                    self.logger.error(
                        "Token callback failed while reporting stalled "
                        "generation: %s",
                        callback_error,
                        exc_info=True,
                    )
            return AIMessage(
                content="",
                additional_kwargs={"error": "no_generation_chunks"},
                tool_calls=[],
            )

        except Exception as exc:
            self.logger.error(
                "Error during streamed model call: %s",
                exc,
                exc_info=True,
            )

        return None