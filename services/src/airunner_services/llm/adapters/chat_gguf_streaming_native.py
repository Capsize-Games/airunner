"""Native llama.cpp streaming helpers for ChatGGUF."""

from __future__ import annotations

import time
from typing import Any, Iterator, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.adapters.chat_gguf_streaming_common import (
    _log_stream_delta,
    _log_stream_start,
    _stream_chat_kwargs,
    _text_chunk,
    finalize_native_tool_call_deltas,
    merge_native_tool_call_deltas,
)
from airunner_services.llm.adapters.chat_gguf_streaming_gpt_oss import (
    _yield_gpt_oss_stream_tail,
)
from airunner_services.llm.gpt_oss_parser import (
    GPTOSSStreamParser,
    has_gpt_oss_markup,
)
from airunner_services.llm.utils.stream_debug import print_stream_debug


def _stream_native_completion(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]],
    run_manager: Optional[CallbackManagerForLLMRun],
    **kwargs: Any,
) -> Iterator[ChatGenerationChunk]:
    """Stream one native llama.cpp chat completion."""
    adapter.logger.info("[ChatGGUF._stream] Starting stream generation")
    converted_messages = adapter._convert_messages(messages)
    adapter.logger.info(
        "[ChatGGUF._stream] Converted %s messages",
        len(converted_messages),
    )
    max_tokens = kwargs.get("max_new_tokens")
    if max_tokens is None:
        max_tokens = kwargs.get("max_tokens", adapter.max_tokens)
    chat_kwargs = _stream_chat_kwargs(adapter, converted_messages, max_tokens, stop)
    adapter._interrupted = False
    full_content: list[str] = []
    native_tool_call_buffers: dict[int, dict[str, Any]] = {}
    call_started = time.perf_counter()
    _log_stream_start(adapter, max_tokens)
    chunk_count = 0
    gpt_oss_parser = (
        GPTOSSStreamParser() if adapter._uses_gpt_oss_parser() else None
    )
    for chunk in adapter._llama.create_chat_completion(**chat_kwargs):
        chunk_count += 1
        if chunk_count == 1:
            adapter.logger.info(
                "[ChatGGUF._stream] First chunk received after %.3fs",
                time.perf_counter() - call_started,
            )
        if adapter._interrupted:
            break
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        _log_stream_delta(chunk_count, delta)
        if delta.get("tool_calls"):
            merge_native_tool_call_deltas(
                adapter,
                native_tool_call_buffers,
                delta["tool_calls"],
            )
        yield from _yield_native_delta(
            adapter,
            delta,
            full_content,
            gpt_oss_parser,
            run_manager,
            chunk_count,
        )
    if gpt_oss_parser is not None:
        yield from _yield_gpt_oss_stream_tail(
            gpt_oss_parser,
            run_manager,
        )
    yield from _final_native_stream_chunks(
        adapter,
        full_content,
        native_tool_call_buffers,
        chunk_count,
        call_started,
    )


def _yield_native_delta(
    adapter: Any,
    delta: dict[str, Any],
    full_content: list[str],
    gpt_oss_parser: Optional[GPTOSSStreamParser],
    run_manager: Optional[CallbackManagerForLLMRun],
    chunk_index: int,
) -> Iterator[ChatGenerationChunk]:
    """Yield chunks for one native stream delta."""
    reasoning_text = delta.get("reasoning_content")
    if "content" in delta and delta["content"]:
        raw_text = delta["content"]
        full_content.append(raw_text)
        text = raw_text
        if gpt_oss_parser is not None or has_gpt_oss_markup(raw_text):
            if gpt_oss_parser is None:
                gpt_oss_parser = GPTOSSStreamParser()
            parsed_delta = gpt_oss_parser.feed(raw_text)
            if parsed_delta.analysis_text:
                if reasoning_text:
                    reasoning_text = (
                        f"{reasoning_text}{parsed_delta.analysis_text}"
                    )
                else:
                    reasoning_text = parsed_delta.analysis_text
            text = parsed_delta.final_text
        yield _text_chunk(text, reasoning_text, run_manager, chunk_index)
        return
    if reasoning_text:
        print_stream_debug(
            "chat_gguf.yield_reasoning",
            chunk_index=chunk_index,
            reasoning_content=reasoning_text,
        )
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                additional_kwargs={"reasoning_content": reasoning_text},
            )
        )


def _final_native_stream_chunks(
    adapter: Any,
    full_content: list[str],
    native_tool_call_buffers: dict[int, dict[str, Any]],
    chunk_count: int,
    call_started: float,
) -> Iterator[ChatGenerationChunk]:
    """Yield final tool-call chunks after one native stream completes."""
    full_text = "".join(full_content)
    adapter.logger.info(
        "[ChatGGUF._stream] Stream loop finished in %.3fs. Total "
        "chunks: %s, content length: %s",
        time.perf_counter() - call_started,
        chunk_count,
        len(full_text),
    )
    gpt_oss_tool_calls = adapter._parse_gpt_oss_commentary_tool_calls(full_text)
    tool_calls = finalize_native_tool_call_deltas(
        adapter,
        native_tool_call_buffers,
    )
    if not tool_calls:
        tool_calls, _ = adapter._extract_tool_calls(full_text)
    if not tool_calls and gpt_oss_tool_calls:
        tool_calls = gpt_oss_tool_calls
    if tool_calls:
        adapter.logger.debug(
            "[TOOL CALL] Parsed %s tool calls from streamed response",
            len(tool_calls),
        )
        yield ChatGenerationChunk(
            message=AIMessageChunk(content="", tool_calls=tool_calls)
        )