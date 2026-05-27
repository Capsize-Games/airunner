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