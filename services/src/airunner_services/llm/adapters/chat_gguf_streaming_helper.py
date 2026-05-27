"""Streaming helpers extracted from the ChatGGUF adapter."""

from __future__ import annotations

from typing import Any, Iterator, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.adapters.chat_gguf_streaming_common import (
    finalize_native_tool_call_deltas,
    merge_native_tool_call_deltas,
    merge_streamed_text,
)
from airunner_services.llm.adapters.chat_gguf_streaming_gpt_oss import (
    _stream_raw_gpt_oss_completion,
)
from airunner_services.llm.adapters.chat_gguf_streaming_native import (
    _stream_native_completion,
)


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
