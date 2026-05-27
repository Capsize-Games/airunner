"""Raw GPT-OSS streaming helpers for ChatGGUF."""

from __future__ import annotations

from typing import Any, Iterator, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.gpt_oss_parser import GPTOSSStreamParser


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


def _yield_gpt_oss_stream_tail(
    gpt_oss_parser: GPTOSSStreamParser,
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Yield the final GPT-OSS parser tail for one native stream."""
    parsed_tail = gpt_oss_parser.finish()
    if parsed_tail.analysis_text:
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                additional_kwargs={
                    "reasoning_content": parsed_tail.analysis_text,
                },
            )
        )
    if parsed_tail.final_text:
        tail_chunk = ChatGenerationChunk(
            message=AIMessageChunk(content=parsed_tail.final_text)
        )
        if run_manager:
            run_manager.on_llm_new_token(
                parsed_tail.final_text,
                chunk=tail_chunk,
            )
        yield tail_chunk