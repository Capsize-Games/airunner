"""GPT-OSS streaming tail helpers for ChatGGUF."""

from __future__ import annotations

from typing import Any, Iterator, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.gpt_oss_parser import GPTOSSStreamParser


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