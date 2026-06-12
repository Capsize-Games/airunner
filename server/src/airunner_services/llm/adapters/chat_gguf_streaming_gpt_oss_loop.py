"""Raw GPT-OSS streaming loop helpers for ChatGGUF."""

from __future__ import annotations

from typing import Any, Iterator, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.adapters.chat_gguf_streaming_gpt_oss_tail import (
    _continued_prefilled_raw_text,
    _final_raw_gpt_oss_chunks,
)
from airunner_services.llm.gpt_oss_parser import GPTOSSStreamParser


def _stream_raw_gpt_oss_completion(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]],
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Stream one raw GPT-OSS Harmony completion."""
    completion_kwargs, parser, forced_tool_name = _raw_gpt_oss_state(
        adapter, messages, stop
    )
    raw_text, saw_visible_text = yield from _yield_raw_gpt_oss_deltas(
        adapter, completion_kwargs, parser, forced_tool_name, run_manager
    )
    yield from _final_raw_gpt_oss_chunks(
        adapter,
        parser,
        raw_text,
        forced_tool_name,
        run_manager,
        saw_visible_text,
    )


def _yield_raw_gpt_oss_deltas(
    adapter: Any,
    completion_kwargs: dict[str, Any],
    parser: GPTOSSStreamParser,
    forced_tool_name: Optional[str],
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Yield raw GPT-OSS deltas and return the completed raw text."""
    full_content: list[str] = []
    saw_visible_text = False
    for chunk in adapter._llama.create_completion(**completion_kwargs):
        if adapter._interrupted:
            break
        if not (raw_text := _completion_text(chunk)):
            continue
        full_content.append(raw_text)
        chunk_visible = yield from _yield_raw_gpt_oss_delta(
            parser, raw_text, forced_tool_name, run_manager
        )
        saw_visible_text = saw_visible_text or chunk_visible
    return (
        _completed_raw_text(
            adapter, completion_kwargs, full_content, forced_tool_name
        ),
        saw_visible_text,
    )


def _raw_gpt_oss_state(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]],
) -> tuple[dict[str, Any], GPTOSSStreamParser, Optional[str]]:
    """Build stream state for one raw GPT-OSS completion."""
    return (
        adapter._build_gpt_oss_completion_kwargs(messages, stop, stream=True),
        GPTOSSStreamParser(),
        adapter._forced_gpt_oss_tool_name(),
    )


def _completion_text(chunk: dict[str, Any]) -> str:
    """Return the raw text payload from one completion chunk."""
    return chunk.get("choices", [{}])[0].get("text", "")


def _yield_raw_gpt_oss_delta(
    parser: GPTOSSStreamParser,
    raw_text: str,
    forced_tool_name: Optional[str],
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Yield parsed reasoning/text chunks from one raw GPT-OSS delta."""
    parsed_delta = parser.feed(raw_text)
    if parsed_delta.analysis_text:
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                additional_kwargs={
                    "reasoning_content": parsed_delta.analysis_text
                },
            )
        )
    visible_text_emitted = bool(
        parsed_delta.final_text and not forced_tool_name
    )
    if visible_text_emitted:
        yield _raw_text_chunk(parsed_delta.final_text, run_manager)
    return visible_text_emitted


def _raw_text_chunk(
    text: str,
    run_manager: Optional[CallbackManagerForLLMRun],
) -> ChatGenerationChunk:
    """Return one streamed GPT-OSS text chunk and notify callbacks."""
    chunk_msg = ChatGenerationChunk(message=AIMessageChunk(content=text))
    if run_manager:
        run_manager.on_llm_new_token(text, chunk=chunk_msg)
    return chunk_msg


def _completed_raw_text(
    adapter: Any,
    completion_kwargs: dict[str, Any],
    full_content: list[str],
    forced_tool_name: Optional[str],
) -> str:
    """Return the completed raw GPT-OSS transcript after continuation."""
    raw_text = "".join(full_content)
    if forced_tool_name:
        return _continued_prefilled_raw_text(
            adapter, completion_kwargs, raw_text
        )
    return raw_text
