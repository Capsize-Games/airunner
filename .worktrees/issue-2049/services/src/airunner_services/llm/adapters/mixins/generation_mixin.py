"""Generation operations for HuggingFace chat models."""

from typing import List, Optional, Any, Iterator

import torch
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
)
from langchain_core.outputs import (
    ChatGeneration,
    ChatGenerationChunk,
    ChatResult,
)
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

from airunner_services.llm.adapters.mixins.generation_streaming_helpers import (
    build_generation_kwargs,
    create_tool_call_chunk,
    create_streamer,
    parse_stream_tool_calls,
    start_generation_thread,
    stream_tokens,
)
from airunner_services.llm.adapters.mixins.generation_response_helpers import (
    decode_response,
    parse_tool_calls_if_enabled,
)
from airunner_services.llm.adapters.mixins.generation_model_helpers import (
    get_token_ids,
    run_generation,
)
from airunner_services.llm.adapters.mixins.generation_vision_inputs import (
    load_image_from_source,
    prepare_vision_inputs,
    resize_image_for_quantized_model,
)
from airunner_services.llm.tool_call_identity import tool_call_identity_key


class GenerationMixin:
    """Handles text generation for chat models.

    This mixin provides functionality for:
    - Non-streaming generation (_generate)
    - Streaming generation (_stream)
    - Token ID management
    - Tool call parsing from generated text
    """

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages.

        Args:
            messages: List of input messages
            stop: Optional stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional generation parameters

        Returns:
            ChatResult with generated response
        """
        prompt = self._messages_to_prompt(messages)
        inputs = self._prepare_inputs(prompt)
        outputs = _run_non_stream_generation(self, inputs, kwargs)
        response_text = self._decode_response(outputs, inputs)
        tool_calls, cleaned_text = _response_tool_calls(
            self,
            response_text,
            kwargs,
        )
        return _generation_result(cleaned_text, tool_calls)

    def _prepare_inputs(self, prompt):
        """Prepare model inputs from prompt.

        Args:
            prompt: Text prompt or token list

        Returns:
            Dictionary with input tensors
        """
        # Check if we have pending images for vision processing
        pending_images = getattr(self, "_pending_images", [])
        
        if pending_images and hasattr(self, "processor") and self.processor:
            # Vision model with images - use processor
            return self._prepare_vision_inputs(prompt, pending_images)
        
        if isinstance(prompt, list):
            # Token list from Mistral native tokenizer - create attention mask too
            input_ids = torch.tensor([prompt]).to(self.model.device)
            attention_mask = torch.ones_like(input_ids)
            return {"input_ids": input_ids, "attention_mask": attention_mask}
        else:
            # Get max length from model config, default to 131072 for modern LLMs
            max_length = getattr(self.model.config, "max_position_embeddings", 131072)
            # CRITICAL: add_special_tokens=False because the chat template already
            # includes the BOS token (<s>). Without this, we get double <s><s>
            # which corrupts the model output.
            return self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=max_length,
                add_special_tokens=False,
            ).to(self.model.device)

    def _prepare_vision_inputs(self, prompt, image_urls):
        """Prepare inputs for vision model with images.
        
        Args:
            prompt: Text prompt string
            image_urls: List of image sources (data URLs, http/https, file paths, PIL, bytes)
            
        Returns:
            Dictionary with input tensors including pixel_values
        """
        return prepare_vision_inputs(self, prompt, image_urls)

    def _resize_image_for_quantized_model(self, image, max_size: int = 768):
        """Resize image to prevent garbage output from quantized vision models.
        
        Some 4-bit quantized vision models produce corrupted output when
        processing images larger than approximately 640x640 pixels. This method
        resizes images to stay within safe bounds while preserving aspect ratio.
        
        Args:
            image: PIL Image to resize
            max_size: Maximum dimension (width or height) in pixels
            
        Returns:
            Resized PIL Image if needed, otherwise original image
        """
        return resize_image_for_quantized_model(self, image, max_size=max_size)

    def _load_image_from_source(self, source):
        """Best-effort conversion of various image sources to PIL.Image."""
        return load_image_from_source(self, source)

    def _decode_response(self, outputs, inputs):
        """Decode generated tokens to text.

        Args:
            outputs: Generated token sequences
            inputs: Original input tensors

        Returns:
            Decoded response text
        """
        return decode_response(self, outputs, inputs)

    def _parse_tool_calls_if_enabled(self, response_text, kwargs):
        """Parse tool calls from response if tools are bound.

        Args:
            response_text: Generated response text
            kwargs: Generation parameters

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        return parse_tool_calls_if_enabled(self, response_text, kwargs)

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream response from messages using a HuggingFace streamer.

        Args:
            messages: List of input messages
            stop: Optional stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional generation parameters

        Yields:
            ChatGenerationChunk objects with streamed content
        """
        streamer, thread, full_response, has_tools = _start_stream_generation(
            self, messages, kwargs
        )
        try:
            yield from _stream_response_chunks(
                self,
                streamer,
                run_manager,
                full_response,
            )
        finally:
            thread.join()
        yield from _final_stream_tool_call_chunks(self, full_response, kwargs, has_tools)

    def _deduplicate_tool_calls(self, tool_calls: List[dict]) -> List[dict]:
        """Remove duplicate consecutive tool calls with identical name/args.

        Args:
            tool_calls: Raw tool call list extracted from model output

        Returns:
            Filtered tool call list
        """
        seen = set()
        deduped = []
        for call in tool_calls:
            signature = tool_call_identity_key(call)
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(call)
        return deduped


def _run_non_stream_generation(
    adapter: Any,
    inputs: Any,
    kwargs: dict[str, Any],
) -> Any:
    """Run one non-streaming generation request for the adapter."""
    eos_token_id, pad_token_id = get_token_ids(adapter)
    return run_generation(adapter, inputs, eos_token_id, pad_token_id, kwargs)


def _response_tool_calls(
    adapter: Any,
    response_text: str,
    kwargs: dict[str, Any],
) -> tuple[Any, str]:
    """Parse and deduplicate tool calls from one generated response."""
    tool_calls, cleaned_text = adapter._parse_tool_calls_if_enabled(
        response_text,
        kwargs,
    )
    if tool_calls:
        tool_calls = adapter._deduplicate_tool_calls(tool_calls)
    return tool_calls, cleaned_text


def _generation_result(cleaned_text: str, tool_calls: Any) -> ChatResult:
    """Wrap generated text and tool calls in a ChatResult."""
    message = AIMessage(
        content=cleaned_text,
        tool_calls=tool_calls or [],
        id=_tool_message_id(tool_calls),
    )
    return ChatResult(generations=[ChatGeneration(message=message)])


def _tool_message_id(tool_calls: Any) -> Optional[str]:
    """Return a stable AI message ID when tool calls were emitted."""
    if not tool_calls:
        return None
    first_tool_id = tool_calls[0].get("id", "")
    return f"ai-tool-{first_tool_id}" if first_tool_id else None


def _start_stream_generation(
    adapter: Any,
    messages: List[BaseMessage],
    kwargs: dict[str, Any],
) -> tuple[Any, Any, list[str], bool]:
    """Prepare streamer state and launch the generation thread."""
    prompt = adapter._messages_to_prompt(messages)
    inputs = adapter._prepare_inputs(prompt)
    streamer = create_streamer(adapter)
    adapter._interrupted = False
    generation_kwargs = build_generation_kwargs(adapter, inputs, streamer, kwargs)
    thread = start_generation_thread(adapter, generation_kwargs)
    return streamer, thread, [], bool(adapter.tools)


def _stream_response_chunks(
    adapter: Any,
    streamer: Any,
    run_manager: Any,
    full_response: list[str],
) -> Iterator[ChatGenerationChunk]:
    """Yield streamed response chunks from the active generation thread."""
    yield from stream_tokens(adapter, streamer, run_manager, full_response)


def _final_stream_tool_call_chunks(
    adapter: Any,
    full_response: list[str],
    kwargs: dict[str, Any],
    has_tools: bool,
) -> Iterator[ChatGenerationChunk]:
    """Yield the final streamed tool-call chunk when tools were detected."""
    if not has_tools:
        return
    response_text = "".join(full_response)
    tool_calls = parse_stream_tool_calls(adapter, response_text, kwargs)
    if tool_calls:
        yield create_tool_call_chunk(adapter._deduplicate_tool_calls(tool_calls))
