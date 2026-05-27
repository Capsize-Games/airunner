"""Streaming helpers extracted from the ChatGGUF adapter."""

from __future__ import annotations

import time
from typing import Any, Iterator, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.gpt_oss_parser import (
    GPTOSSStreamParser,
    has_gpt_oss_markup,
)
from airunner_services.llm.utils.stream_debug import print_stream_debug


def merge_streamed_text(existing: str, fragment: str) -> str:
    """Merge one streamed text fragment without duplicating overlap."""
    if not existing or not fragment:
        return existing + fragment
    if fragment == existing or existing.endswith(fragment):
        return existing
    if fragment.startswith(existing):
        return fragment
    max_overlap = min(len(existing), len(fragment))
    for overlap in range(max_overlap, 0, -1):
        if existing.endswith(fragment[:overlap]):
            return existing + fragment[overlap:]
    return existing + fragment


def merge_native_tool_call_deltas(
    adapter: Any,
    tool_call_buffers: dict[int, dict[str, Any]],
    raw_tool_calls: Optional[list[dict[str, Any]]],
) -> None:
    """Merge streamed native tool call deltas into one buffer map."""
    for raw_call in raw_tool_calls or []:
        index = raw_call.get("index", len(tool_call_buffers))
        buffer = tool_call_buffers.setdefault(
            index,
            {
                "id": None,
                "type": "function",
                "function": {"name": "", "arguments": ""},
            },
        )
        if raw_call.get("id"):
            buffer["id"] = raw_call["id"]
        if raw_call.get("type"):
            buffer["type"] = raw_call["type"]
        function = raw_call.get("function") or {}
        if function.get("name"):
            buffer["function"]["name"] = merge_streamed_text(
                buffer["function"]["name"],
                function["name"],
            )
        if function.get("arguments"):
            buffer["function"]["arguments"] = merge_streamed_text(
                buffer["function"]["arguments"],
                function["arguments"],
            )


def finalize_native_tool_call_deltas(
    adapter: Any,
    tool_call_buffers: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert buffered streamed tool call deltas into normalized calls."""
    if not tool_call_buffers:
        return []
    ordered_calls = [tool_call_buffers[index] for index in sorted(tool_call_buffers)]
    return adapter._parse_native_tool_calls(ordered_calls)


def stream_chat_result(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any,
) -> Iterator[ChatGenerationChunk]:
    """Stream chat chunks through llama.cpp."""
    if adapter._use_raw_gpt_oss_completion():
        yield from _stream_raw_gpt_oss_completion(
            adapter,
            messages,
            stop,
            run_manager,
        )
        return
    yield from _stream_native_completion(
        adapter,
        messages,
        stop,
        run_manager,
        **kwargs,
    )


def _stream_raw_gpt_oss_completion(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]],
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Stream one raw GPT-OSS Harmony completion."""
    completion_kwargs = adapter._build_gpt_oss_completion_kwargs(
        messages,
        stop,
        stream=True,
    )
    full_content: list[str] = []
    parser = GPTOSSStreamParser()
    forced_tool_name = adapter._forced_gpt_oss_tool_name()
    for chunk in adapter._llama.create_completion(**completion_kwargs):
        if adapter._interrupted:
            break
        raw_text = chunk.get("choices", [{}])[0].get("text", "")
        if not raw_text:
            continue
        full_content.append(raw_text)
        parsed_delta = parser.feed(raw_text)
        if parsed_delta.analysis_text:
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    additional_kwargs={
                        "reasoning_content": parsed_delta.analysis_text,
                    },
                )
            )
        if parsed_delta.final_text and not forced_tool_name:
            chunk_msg = ChatGenerationChunk(
                message=AIMessageChunk(content=parsed_delta.final_text)
            )
            if run_manager:
                run_manager.on_llm_new_token(
                    parsed_delta.final_text,
                    chunk=chunk_msg,
                )
            yield chunk_msg
    raw_text = "".join(full_content)
    if forced_tool_name:
        raw_text = _continued_prefilled_raw_text(
            adapter,
            completion_kwargs,
            raw_text,
        )
    yield from _final_raw_gpt_oss_chunks(
        adapter,
        parser,
        raw_text,
        forced_tool_name,
        run_manager,
    )


def _continued_prefilled_raw_text(
    adapter: Any,
    completion_kwargs: dict[str, Any],
    raw_text: str,
) -> str:
    """Continue one forced prefilled GPT-OSS tool payload if needed."""
    continuation_kwargs = dict(completion_kwargs)
    continuation_kwargs["stream"] = False
    return adapter._continue_prefilled_gpt_oss_tool_call(
        continuation_kwargs,
        raw_text,
    )


def _final_raw_gpt_oss_chunks(
    adapter: Any,
    parser: GPTOSSStreamParser,
    raw_text: str,
    forced_tool_name: Optional[str],
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Yield the final chunks for one raw GPT-OSS stream."""
    parsed_tail = parser.finish()
    if parsed_tail.analysis_text:
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                additional_kwargs={
                    "reasoning_content": parsed_tail.analysis_text,
                },
            )
        )
    if parsed_tail.final_text and not forced_tool_name:
        tail_chunk = ChatGenerationChunk(
            message=AIMessageChunk(content=parsed_tail.final_text)
        )
        if run_manager:
            run_manager.on_llm_new_token(
                parsed_tail.final_text,
                chunk=tail_chunk,
            )
        yield tail_chunk
    tool_calls = adapter._parse_gpt_oss_commentary_tool_calls(raw_text)
    if not tool_calls:
        tool_calls = adapter._parse_prefilled_gpt_oss_tool_call(raw_text)
    if not tool_calls:
        tool_calls, cleaned_text = adapter._extract_tool_calls(raw_text)
    else:
        cleaned_text = ""
    if tool_calls:
        yield ChatGenerationChunk(
            message=AIMessageChunk(content="", tool_calls=tool_calls)
        )
    elif forced_tool_name and cleaned_text:
        fallback_chunk = ChatGenerationChunk(
            message=AIMessageChunk(content=cleaned_text)
        )
        if run_manager:
            run_manager.on_llm_new_token(cleaned_text, chunk=fallback_chunk)
        yield fallback_chunk


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
    gpt_oss_parser = GPTOSSStreamParser() if adapter._uses_gpt_oss_parser() else None
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


def _stream_chat_kwargs(
    adapter: Any,
    converted_messages: list[dict[str, Any]],
    max_tokens: int,
    stop: Optional[list[str]],
) -> dict[str, Any]:
    """Build one llama.cpp streaming chat kwargs payload."""
    chat_kwargs = {
        "messages": converted_messages,
        "max_tokens": max_tokens,
        "temperature": adapter.temperature,
        "top_p": adapter.top_p,
        "top_k": adapter.top_k,
        "min_p": adapter.min_p,
        "repeat_penalty": adapter.repeat_penalty,
        "stream": True,
    }
    if stop:
        chat_kwargs["stop"] = stop
    if adapter._use_native_tool_calling():
        chat_kwargs["tools"] = adapter.tools
        if adapter.tool_choice is not None:
            chat_kwargs["tool_choice"] = adapter.tool_choice
    return chat_kwargs


def _log_stream_start(adapter: Any, max_tokens: int) -> None:
    """Log the start of one streaming llama.cpp request."""
    adapter.logger.info(
        "[ChatGGUF._stream] Calling create_chat_completion with "
        "max_tokens=%s",
        max_tokens,
    )
    adapter.logger.info(
        "[ChatGGUF._stream] Number of tools bound: %s",
        len(adapter.tools) if adapter.tools else 0,
    )
    adapter.logger.info(
        "[ChatGGUF._stream] tool_choice: %s",
        adapter.tool_choice,
    )


def _log_stream_delta(chunk_index: int, delta: dict[str, Any]) -> None:
    """Log one streaming delta through the shared debug helper."""
    print_stream_debug(
        "chat_gguf.delta",
        chunk_index=chunk_index,
        content=delta.get("content"),
        reasoning_content=delta.get("reasoning_content"),
        tool_calls=delta.get("tool_calls"),
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
                    reasoning_text = f"{reasoning_text}{parsed_delta.analysis_text}"
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


def _text_chunk(
    text: str,
    reasoning_text: Optional[str],
    run_manager: Optional[CallbackManagerForLLMRun],
    chunk_index: int,
) -> ChatGenerationChunk:
    """Return one text chunk and notify the run manager when needed."""
    additional_kwargs = {}
    if reasoning_text:
        additional_kwargs["reasoning_content"] = reasoning_text
    chunk = ChatGenerationChunk(
        message=AIMessageChunk(
            content=text,
            additional_kwargs=additional_kwargs,
        )
    )
    print_stream_debug(
        "chat_gguf.yield",
        chunk_index=chunk_index,
        content=text,
        reasoning_content=reasoning_text,
    )
    if run_manager:
        run_manager.on_llm_new_token(text, chunk=chunk)
    return chunk


def _yield_gpt_oss_stream_tail(
    gpt_oss_parser: GPTOSSStreamParser,
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Yield the final GPT-OSS parser tail for one native stream."""
    parsed_tail = gpt_oss_parser.finish()
    if parsed_tail.analysis_text:
        print_stream_debug(
            "chat_gguf.tail_reasoning",
            reasoning_content=parsed_tail.analysis_text,
        )
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                additional_kwargs={
                    "reasoning_content": parsed_tail.analysis_text,
                },
            )
        )
    if parsed_tail.final_text:
        print_stream_debug(
            "chat_gguf.tail_final",
            content=parsed_tail.final_text,
        )
        tail_chunk = ChatGenerationChunk(
            message=AIMessageChunk(content=parsed_tail.final_text)
        )
        if run_manager:
            run_manager.on_llm_new_token(
                parsed_tail.final_text,
                chunk=tail_chunk,
            )
        yield tail_chunk


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
    tool_calls = finalize_native_tool_call_deltas(adapter, native_tool_call_buffers)
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