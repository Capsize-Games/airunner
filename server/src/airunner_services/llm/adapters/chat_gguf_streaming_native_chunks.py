"""Chunk-yield helpers for native GGUF streaming."""

from __future__ import annotations

import time
from typing import Any, Iterator, Optional

from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.adapters.chat_gguf_streaming_payloads import (
    text_chunk,
)
from airunner_services.llm.gpt_oss_parser import (
    GPTOSSStreamParser,
    has_gpt_oss_markup,
)
from airunner_services.llm.utils.stream_debug import print_stream_debug


def _parse_native_text_delta(
    raw_text: str,
    gpt_oss_parser: Optional[GPTOSSStreamParser],
) -> tuple[str, Optional[str]]:
    """Parse one streamed delta when GPT-OSS markup is present."""
    if gpt_oss_parser is None and not has_gpt_oss_markup(raw_text):
        return raw_text, None
    parser = gpt_oss_parser or GPTOSSStreamParser()
    parsed_delta = parser.feed(raw_text)
    return parsed_delta.final_text, parsed_delta.analysis_text


def _merge_reasoning_text(
    reasoning_text: Optional[str],
    analysis_text: Optional[str],
) -> Optional[str]:
    """Combine reasoning text from the delta and GPT-OSS parser."""
    if not analysis_text:
        return reasoning_text
    if reasoning_text:
        return f"{reasoning_text}{analysis_text}"
    return analysis_text


def _content_chunk(
    delta: dict[str, Any],
    full_content: list[str],
    gpt_oss_parser: Optional[GPTOSSStreamParser],
    run_manager: Any,
    chunk_index: int,
) -> ChatGenerationChunk:
    """Build one streamed content chunk from a native delta."""
    raw_text = delta["content"]
    full_content.append(raw_text)
    text, analysis_text = _parse_native_text_delta(raw_text, gpt_oss_parser)
    reasoning_text = _merge_reasoning_text(
        delta.get("reasoning_content"),
        analysis_text,
    )
    return text_chunk(text, reasoning_text, run_manager, chunk_index)


def _reasoning_only_chunk(
    reasoning_text: str,
    chunk_index: int,
) -> ChatGenerationChunk:
    """Build one reasoning-only streaming chunk."""
    print_stream_debug(
        "chat_gguf.yield_reasoning",
        chunk_index=chunk_index,
        reasoning_content=reasoning_text,
    )
    return ChatGenerationChunk(
        message=AIMessageChunk(
            content="",
            additional_kwargs={"reasoning_content": reasoning_text},
        )
    )


def yield_native_delta(
    adapter: Any,
    delta: dict[str, Any],
    full_content: list[str],
    gpt_oss_parser: Optional[GPTOSSStreamParser],
    run_manager: Any,
    chunk_index: int,
) -> Iterator[ChatGenerationChunk]:
    """Yield chunks for one native stream delta."""
    if "content" in delta and delta["content"]:
        yield _content_chunk(
            delta,
            full_content,
            gpt_oss_parser,
            run_manager,
            chunk_index,
        )
        return
    reasoning_text = delta.get("reasoning_content")
    if reasoning_text:
        yield _reasoning_only_chunk(reasoning_text, chunk_index)


def _log_stream_finish(
    adapter: Any,
    call_started: float,
    chunk_count: int,
    full_text: str,
) -> None:
    """Log one completed native stream summary."""
    adapter.logger.info(
        "[ChatGGUF._stream] Stream loop finished in %.3fs. Total "
        "chunks: %s, content length: %s",
        time.perf_counter() - call_started,
        chunk_count,
        len(full_text),
    )


def _resolve_stream_tool_calls(
    adapter: Any,
    full_text: str,
    native_tool_call_buffers: dict[int, dict[str, Any]],
    finalize_native_tool_call_deltas: Any,
) -> Any:
    """Resolve tool calls emitted during one native stream."""
    gpt_oss_tool_calls = adapter._parse_gpt_oss_commentary_tool_calls(
        full_text
    )
    tool_calls = finalize_native_tool_call_deltas(
        adapter,
        native_tool_call_buffers,
    )
    if not tool_calls:
        tool_calls, _ = adapter._extract_tool_calls(full_text)
    if tool_calls or not gpt_oss_tool_calls:
        return tool_calls
    return gpt_oss_tool_calls


def _tool_call_chunk(tool_calls: Any) -> ChatGenerationChunk:
    """Build one final tool-call chunk."""
    return ChatGenerationChunk(
        message=AIMessageChunk(content="", tool_calls=tool_calls)
    )


def final_native_stream_chunks(
    adapter: Any,
    full_content: list[str],
    native_tool_call_buffers: dict[int, dict[str, Any]],
    chunk_count: int,
    call_started: float,
    finalize_native_tool_call_deltas: Any,
) -> Iterator[ChatGenerationChunk]:
    """Yield final tool-call chunks after one native stream completes."""
    full_text = "".join(full_content)
    _log_stream_finish(adapter, call_started, chunk_count, full_text)
    tool_calls = _resolve_stream_tool_calls(
        adapter,
        full_text,
        native_tool_call_buffers,
        finalize_native_tool_call_deltas,
    )
    if tool_calls:
        _log_stream_tool_calls(adapter, tool_calls)
        yield _tool_call_chunk(tool_calls)


def _log_stream_tool_calls(adapter: Any, tool_calls: Any) -> None:
    """Log parsed tool calls emitted during native streaming."""
    adapter.logger.debug(
        "[TOOL CALL] Parsed %s tool calls from streamed response",
        len(tool_calls),
    )
