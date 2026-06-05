"""Native llama.cpp streaming helpers for ChatGGUF."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.adapters.chat_gguf_streaming_common import (
    _log_stream_delta,
    _log_stream_start,
    finalize_native_tool_call_deltas,
    merge_native_tool_call_deltas,
)
from airunner_services.llm.adapters.chat_gguf_streaming_native_chunks import (
    final_native_stream_chunks,
    yield_native_delta,
)
from airunner_services.llm.adapters.chat_gguf_streaming_gpt_oss_tail import (
    _yield_gpt_oss_stream_tail,
)
from airunner_services.llm.adapters.chat_gguf_streaming_payloads import (
    stream_chat_kwargs,
)
from airunner_services.llm.adapters.chat_gguf_generation_helper import (
    effective_max_tokens,
)
from airunner_services.llm.gpt_oss_parser import (
    GPTOSSStreamParser,
)


@dataclass
class NativeStreamState:
    """Mutable state carried across one native llama.cpp stream."""

    chat_kwargs: dict[str, Any]
    full_content: list[str]
    native_tool_call_buffers: dict[int, dict[str, Any]]
    call_started: float
    gpt_oss_parser: Optional[GPTOSSStreamParser]


def _stream_native_completion(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]],
    run_manager: Optional[CallbackManagerForLLMRun],
    **kwargs: Any,
) -> Iterator[ChatGenerationChunk]:
    """Stream one native llama.cpp chat completion."""
    state = _native_stream_state(adapter, messages, stop, kwargs)
    chunk_count = yield from _yield_native_stream_deltas(
        adapter,
        state,
        run_manager,
    )
    yield from _yield_native_stream_tail(
        adapter, state, run_manager, chunk_count
    )


def _native_stream_state(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]],
    kwargs: dict[str, Any],
) -> NativeStreamState:
    """Build the initial state for one native llama.cpp stream."""
    adapter.logger.info("[ChatGGUF._stream] Starting stream generation")
    converted_messages = adapter._convert_messages(messages)
    adapter.logger.info(
        "[ChatGGUF._stream] Converted %s messages", len(converted_messages)
    )
    max_tokens = _stream_max_tokens(adapter, kwargs)
    adapter._interrupted = False
    call_started = time.perf_counter()
    _log_stream_start(adapter, max_tokens)
    return NativeStreamState(
        chat_kwargs=stream_chat_kwargs(
            adapter, converted_messages, max_tokens, stop
        ),
        full_content=[],
        native_tool_call_buffers={},
        call_started=call_started,
        gpt_oss_parser=_native_gpt_oss_parser(adapter),
    )


def _yield_native_stream_deltas(
    adapter: Any,
    state: NativeStreamState,
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Yield native stream deltas and return the final chunk count."""
    chunk_count = 0
    for chunk_count, chunk in enumerate(
        adapter._llama.create_chat_completion(**state.chat_kwargs),
        start=1,
    ):
        _log_first_native_chunk(adapter, chunk_count, state.call_started)
        if adapter._interrupted:
            break
        yield from _yield_native_stream_delta(
            adapter,
            state,
            _native_delta(chunk),
            run_manager,
            chunk_count,
        )
    return chunk_count


def _yield_native_stream_delta(
    adapter: Any,
    state: NativeStreamState,
    delta: dict[str, Any],
    run_manager: Optional[CallbackManagerForLLMRun],
    chunk_count: int,
) -> Iterator[ChatGenerationChunk]:
    """Yield one native stream delta after logging and tool-call merging."""
    _log_stream_delta(chunk_count, delta)
    _record_native_tool_calls(adapter, state.native_tool_call_buffers, delta)
    yield from yield_native_delta(
        adapter,
        delta,
        state.full_content,
        state.gpt_oss_parser,
        run_manager,
        chunk_count,
    )


def _native_gpt_oss_parser(adapter: Any) -> Optional[GPTOSSStreamParser]:
    """Return a GPT-OSS parser when the native stream needs one."""
    if adapter._uses_gpt_oss_parser():
        return GPTOSSStreamParser()
    return None


def _yield_native_stream_tail(
    adapter: Any,
    state: NativeStreamState,
    run_manager: Optional[CallbackManagerForLLMRun],
    chunk_count: int,
) -> Iterator[ChatGenerationChunk]:
    """Yield the GPT-OSS and tool-call tail for a native stream."""
    if state.gpt_oss_parser is not None:
        yield from _yield_gpt_oss_stream_tail(
            state.gpt_oss_parser, run_manager
        )
    yield from final_native_stream_chunks(
        adapter,
        state.full_content,
        state.native_tool_call_buffers,
        chunk_count,
        state.call_started,
        finalize_native_tool_call_deltas,
    )


def _stream_max_tokens(
    adapter: Any,
    kwargs: dict[str, Any],
) -> Optional[int]:
    """Return the effective max-token budget for a native stream."""
    max_tokens = kwargs.get("max_new_tokens")
    if max_tokens is None:
        max_tokens = kwargs.get("max_tokens", adapter.max_tokens)
    return effective_max_tokens(adapter, max_tokens)


def _log_first_native_chunk(
    adapter: Any,
    chunk_count: int,
    call_started: float,
) -> None:
    """Log when the first native stream chunk arrives."""
    if chunk_count != 1:
        return
    adapter.logger.info(
        "[ChatGGUF._stream] First chunk received after %.3fs",
        time.perf_counter() - call_started,
    )


def _native_delta(chunk: dict[str, Any]) -> dict[str, Any]:
    """Return the delta payload from one native chat-completion chunk."""
    return chunk.get("choices", [{}])[0].get("delta", {})


def _record_native_tool_calls(
    adapter: Any,
    native_tool_call_buffers: dict[int, dict[str, Any]],
    delta: dict[str, Any],
) -> None:
    """Record streamed native tool-call deltas when present."""
    if delta.get("tool_calls"):
        merge_native_tool_call_deltas(
            adapter,
            native_tool_call_buffers,
            delta["tool_calls"],
        )
