"""Streaming helpers for HuggingFace generation mixins."""

from __future__ import annotations

import threading
import traceback
from typing import Any, Iterator

from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from transformers.generation.streamers import TextIteratorStreamer

from airunner_services.llm.adapters.mixins.generation_model_helpers import (
    get_token_ids,
)
from airunner_services.llm.managers.external_condition_stopping_criteria import (
    ExternalConditionStoppingCriteria,
)


def create_streamer(adapter: Any) -> TextIteratorStreamer:
    """Create the streaming iterator used by model.generate()."""
    skip_special = not adapter.use_mistral_native
    return TextIteratorStreamer(
        adapter.tokenizer,
        skip_prompt=True,
        skip_special_tokens=skip_special,
    )


def build_generation_kwargs(
    adapter: Any,
    inputs: dict,
    streamer: TextIteratorStreamer,
    kwargs: dict,
) -> dict:
    """Build keyword arguments for streamed generation."""
    eos_token_id, pad_token_id = get_token_ids(adapter)
    return {
        **inputs,
        **_stream_sampling_kwargs(
            adapter,
            kwargs,
            eos_token_id,
            pad_token_id,
        ),
        "streamer": streamer,
        "stopping_criteria": _stream_stopping_criteria(adapter),
        "use_cache": True,
    }


def _stream_sampling_kwargs(
    adapter: Any,
    kwargs: dict,
    eos_token_id: int,
    pad_token_id: int,
) -> dict[str, Any]:
    """Build shared sampling kwargs for streamed generation."""
    return {
        "max_new_tokens": kwargs.get("max_new_tokens", adapter.max_new_tokens),
        "temperature": kwargs.get("temperature", adapter.temperature),
        "top_p": kwargs.get("top_p", adapter.top_p),
        "top_k": kwargs.get("top_k", adapter.top_k),
        "repetition_penalty": kwargs.get(
            "repetition_penalty",
            adapter.repetition_penalty,
        ),
        "do_sample": kwargs.get("do_sample", adapter.do_sample),
        "pad_token_id": pad_token_id,
        "eos_token_id": eos_token_id,
    }


def _stream_stopping_criteria(adapter: Any) -> list[Any]:
    """Build stopping criteria for streamed generation."""
    return [ExternalConditionStoppingCriteria(adapter.should_stop_generation)]


def start_generation_thread(
    adapter: Any,
    generation_kwargs: dict,
) -> threading.Thread:
    """Start generation in a background thread."""
    thread = threading.Thread(
        target=_run_generation_with_error_handling,
        args=(adapter, generation_kwargs),
    )
    thread.daemon = True
    thread.start()
    return thread


def _run_generation_with_error_handling(
    adapter: Any,
    generation_kwargs: dict,
) -> None:
    """Run model.generate() and unblock the streamer on failure."""
    try:
        adapter.logger.debug("Starting model.generate() in background thread")
        adapter.model.generate(**generation_kwargs)
        adapter.logger.debug("model.generate() completed successfully")
    except Exception as error:
        adapter.logger.error(
            "Generation thread error: %s: %s",
            type(error).__name__,
            error,
        )
        adapter.logger.error(
            "Generation thread traceback:\n%s",
            traceback.format_exc(),
        )
        _signal_streamer_failure(generation_kwargs)


def _signal_streamer_failure(generation_kwargs: dict) -> None:
    """Signal streamer termination after a generation failure."""
    streamer = generation_kwargs.get("streamer")
    if streamer is None:
        return
    try:
        streamer.text_queue.put(None)
    except Exception:
        return


def stream_tokens(
    adapter: Any,
    streamer: TextIteratorStreamer,
    run_manager: Any,
    full_response: list[str],
) -> Iterator[ChatGenerationChunk]:
    """Yield token chunks from one active streamer."""
    for text in streamer:
        if adapter._interrupted:
            adapter.logger.info("Stream interrupted - breaking immediately")
            clear_streamer_queue(streamer)
            break
        if not text:
            continue
        full_response.append(text)
        chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
        if run_manager:
            run_manager.on_llm_new_token(text, chunk=chunk)
        yield chunk


def clear_streamer_queue(streamer: TextIteratorStreamer) -> None:
    """Drain the streamer queue to unblock the generation thread."""
    try:
        while not streamer.text_queue.empty():
            streamer.text_queue.get_nowait()
    except Exception:
        return


def parse_stream_tool_calls(
    adapter: Any,
    response_text: str,
    kwargs: dict,
) -> Any:
    """Parse tool calls from one streamed response body."""
    if kwargs.get("disable_tool_parsing", False):
        return None
    if adapter.tool_calling_mode == "native" and adapter.use_mistral_native:
        tool_calls, _ = adapter._parse_mistral_tool_calls(response_text)
        return _log_stream_tool_calls(adapter, tool_calls, "Mistral native")
    if adapter.tool_calling_mode == "json" and adapter.use_json_mode:
        tool_calls, _ = adapter._parse_json_mode_tool_calls(response_text)
        return _log_stream_tool_calls(adapter, tool_calls, "JSON mode")
    tool_calls, _ = adapter._parse_tool_calls(response_text)
    return _log_stream_tool_calls(adapter, tool_calls, "ReAct")


def _log_stream_tool_calls(
    adapter: Any,
    tool_calls: Any,
    mode_name: str,
) -> Any:
    """Log one stream tool-call summary when calls were found."""
    if tool_calls:
        adapter.logger.debug(
            "%s extracted %s tool call(s) from stream",
            mode_name,
            len(tool_calls),
        )
    return tool_calls


def create_tool_call_chunk(tool_calls: list[dict]) -> ChatGenerationChunk:
    """Create the final streamed chunk that carries tool calls."""
    final_message = AIMessageChunk(
        content="",
        additional_kwargs={"tool_calls": tool_calls},
    )
    final_message.tool_calls = tool_calls
    return ChatGenerationChunk(message=final_message)
