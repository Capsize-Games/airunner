"""GPT-OSS streaming tail helpers for ChatGGUF."""

from __future__ import annotations

from typing import Any, Iterator, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.gpt_oss_parser import (
    GPTOSSStreamParser,
    parse_gpt_oss_response,
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
    saw_visible_text: bool,
) -> Iterator[ChatGenerationChunk]:
    """Yield the final chunks for one raw GPT-OSS stream."""
    parsed_tail = parser.finish()
    yield from _yield_parser_tail(parsed_tail, forced_tool_name, run_manager)
    tool_calls, cleaned_text = _resolved_tool_calls(adapter, raw_text)
    if tool_calls:
        yield _tool_call_chunk(tool_calls)
        return
    tail_text = _final_tail_text(
        raw_text, cleaned_text, forced_tool_name,
        saw_visible_text or bool(parsed_tail.final_text and not forced_tool_name),
    )
    if tail_text:
        yield _text_tail_chunk(tail_text, run_manager)


def _yield_parser_tail(
    parsed_tail: Any,
    forced_tool_name: Optional[str],
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Yield reasoning and final-text chunks from one parser tail."""
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
        yield _text_tail_chunk(parsed_tail.final_text, run_manager)


def _resolved_tool_calls(
    adapter: Any,
    raw_text: str,
) -> tuple[list[dict[str, Any]], str]:
    """Return parsed GPT-OSS tool calls and fallback text."""
    tool_calls = adapter._parse_gpt_oss_commentary_tool_calls(raw_text)
    if tool_calls:
        return tool_calls, ""
    tool_calls = adapter._parse_prefilled_gpt_oss_tool_call(raw_text)
    if tool_calls:
        return tool_calls, ""
    return adapter._extract_tool_calls(raw_text)


def _tool_call_chunk(tool_calls: list[dict[str, Any]]) -> ChatGenerationChunk:
    """Return one final tool-call chunk."""
    return ChatGenerationChunk(
        message=AIMessageChunk(content="", tool_calls=tool_calls)
    )


def _final_tail_text(
    raw_text: str,
    cleaned_text: str,
    forced_tool_name: Optional[str],
    visible_text_emitted: bool,
) -> str:
    """Return final tail text when GPT-OSS streaming emitted none."""
    if forced_tool_name:
        return cleaned_text
    if visible_text_emitted:
        return ""
    return parse_gpt_oss_response(raw_text).content or ""


def _text_tail_chunk(
    text: str,
    run_manager: Optional[CallbackManagerForLLMRun],
) -> ChatGenerationChunk:
    """Return one final text chunk and notify the callback manager."""
    tail_chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
    if run_manager:
        run_manager.on_llm_new_token(text, chunk=tail_chunk)
    return tail_chunk


def _yield_gpt_oss_stream_tail(
    gpt_oss_parser: GPTOSSStreamParser,
    run_manager: Optional[CallbackManagerForLLMRun],
) -> Iterator[ChatGenerationChunk]:
    """Yield the final GPT-OSS parser tail for one native stream."""
    yield from _yield_parser_tail(gpt_oss_parser.finish(), None, run_manager)