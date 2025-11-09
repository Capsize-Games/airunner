"""Generation operations for HuggingFace chat models."""

import sys
import threading
from typing import List, Optional, Any, Iterator

import torch
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    AIMessageChunk,
)
from langchain_core.outputs import (
    ChatGeneration,
    ChatGenerationChunk,
    ChatResult,
)
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from transformers.generation.streamers import TextIteratorStreamer

from airunner.components.llm.managers.external_condition_stopping_criteria import (
    ExternalConditionStoppingCriteria,
)


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

        eos_token_id, pad_token_id = self._get_token_ids()

        outputs = self._run_generation(
            inputs, eos_token_id, pad_token_id, kwargs
        )
        response_text = self._decode_response(outputs, inputs)

        tool_calls, cleaned_text = self._parse_tool_calls_if_enabled(
            response_text, kwargs
        )
        # Deduplicate identical zero-arg tool calls
        if tool_calls:
            tool_calls = self._deduplicate_tool_calls(tool_calls)

        message = AIMessage(content=cleaned_text, tool_calls=tool_calls or [])
        generation = ChatGeneration(message=message)

        return ChatResult(generations=[generation])

    def _prepare_inputs(self, prompt):
        """Prepare model inputs from prompt.

        Args:
            prompt: Text prompt or token list

        Returns:
            Dictionary with input tensors
        """
        if isinstance(prompt, list):
            return {"input_ids": torch.tensor([prompt]).to(self.model.device)}
        else:
            return self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            ).to(self.model.device)

    def _get_token_ids(self):
        """Get EOS and PAD token IDs based on tokenizer type.

        Returns:
            Tuple of (eos_token_id, pad_token_id)
        """
        if self.use_mistral_native and self._mistral_tokenizer:
            eos_token_id = (
                self._mistral_tokenizer.instruct_tokenizer.tokenizer.eos_id
            )
            pad_token_id = eos_token_id
        elif self.tokenizer:
            eos_token_id = self.tokenizer.eos_token_id
            pad_token_id = self.tokenizer.eos_token_id
        else:
            eos_token_id = 2
            pad_token_id = 2
        return eos_token_id, pad_token_id

    def _run_generation(self, inputs, eos_token_id, pad_token_id, kwargs):
        """Run model generation with parameters.

        Args:
            inputs: Input tensors
            eos_token_id: End of sequence token ID
            pad_token_id: Padding token ID
            kwargs: Generation parameters

        Returns:
            Generated token sequences
        """
        with torch.no_grad():
            return self.model.generate(
                **inputs,
                max_new_tokens=kwargs.get(
                    "max_new_tokens", self.max_new_tokens
                ),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                top_k=kwargs.get("top_k", self.top_k),
                repetition_penalty=kwargs.get(
                    "repetition_penalty", self.repetition_penalty
                ),
                do_sample=kwargs.get("do_sample", self.do_sample),
                pad_token_id=pad_token_id,
                eos_token_id=eos_token_id,
            )

    def _decode_response(self, outputs, inputs):
        """Decode generated tokens to text.

        Args:
            outputs: Generated token sequences
            inputs: Original input tensors

        Returns:
            Decoded response text
        """
        input_length = inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_length:]

        if self.use_mistral_native and self._mistral_tokenizer:
            response_text = (
                self._mistral_tokenizer.instruct_tokenizer.tokenizer.decode(
                    generated_tokens.tolist()
                )
            )
            self.logger.debug(
                f"Mistral decoded response length: {len(response_text)}"
            )
        elif self.tokenizer:
            response_text = self.tokenizer.decode(
                generated_tokens, skip_special_tokens=True
            )
        else:
            raise ValueError(
                "No tokenizer available for decoding. "
                "Ensure mistral_common is initialized for Mistral3 models."
            )

        return response_text

    def _parse_tool_calls_if_enabled(self, response_text, kwargs):
        """Parse tool calls from response if tools are bound.

        Args:
            response_text: Generated response text
            kwargs: Generation parameters

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        if not self.tools or kwargs.get("disable_tool_parsing", False):
            return None, response_text

        if self.tool_calling_mode == "native" and self.use_mistral_native:
            tool_calls, cleaned_text = self._parse_mistral_tool_calls(
                response_text
            )
            if tool_calls:
                self.logger.debug(
                    f"Mistral native extracted {len(tool_calls)} tool call(s)"
                )
            return tool_calls, cleaned_text

        elif self.tool_calling_mode == "json" and self.use_json_mode:
            tool_calls, cleaned_text = self._parse_json_mode_tool_calls(
                response_text
            )
            if tool_calls:
                self.logger.debug(
                    f"JSON mode extracted {len(tool_calls)} tool call(s)"
                )
            return tool_calls, cleaned_text

        else:
            tool_calls, cleaned_text = self._parse_tool_calls(response_text)
            if tool_calls:
                self.logger.debug(
                    f"ReAct extracted {len(tool_calls)} tool call(s)"
                )
            return tool_calls, cleaned_text

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
        prompt = self._messages_to_prompt(messages)
        inputs = self._prepare_inputs(prompt)

        streamer = self._create_streamer()
        self._interrupted = False

        generation_kwargs = self._build_generation_kwargs(
            inputs, streamer, kwargs
        )
        self._log_generation_params(generation_kwargs, inputs, kwargs)

        thread = self._start_generation_thread(generation_kwargs)
        full_response = []

        # Collect all streamed tokens
        # If tools are enabled, buffer everything to yield a single complete message
        # Otherwise stream chunks in real-time
        should_buffer = bool(self.tools)

        token_count = 0
        try:
            for chunk in self._stream_tokens(
                streamer, run_manager, full_response
            ):
                token_count += 1
                if not should_buffer:
                    print(
                        f"[STREAM YIELD DEBUG] Yielding content chunk during loop (token #{token_count})",
                        flush=True,
                    )
                    yield chunk
                else:
                    if (
                        token_count % 100 == 0
                    ):  # Log every 100 tokens to reduce spam
                        print(
                            f"[STREAM YIELD DEBUG] Buffered {token_count} tokens so far...",
                            flush=True,
                        )
        finally:
            print(
                f"[STREAM YIELD DEBUG] Stream ended - total tokens buffered: {token_count}",
                flush=True,
            )
            thread.join()

        # Always yield a final complete message
        response_text = "".join(full_response)

        if self.tools:
            print(
                f"[STREAM YIELD DEBUG] Tools enabled, preparing final chunk",
                flush=True,
            )
            # Parse tool calls and get cleaned text
            self._log_stream_completion(response_text, kwargs)
            tool_calls = self._parse_stream_tool_calls(response_text, kwargs)
            _, cleaned_text = self._parse_tool_calls_if_enabled(
                response_text, kwargs
            )

            if tool_calls:
                tool_calls = self._deduplicate_tool_calls(tool_calls)

            # Yield single complete message with both content and tool_calls
            message = AIMessageChunk(
                content=cleaned_text, tool_calls=tool_calls or []
            )
            chunk = ChatGenerationChunk(message=message)

            print(
                f"[STREAM DEBUG] Yielding complete message - content: '{cleaned_text}', tool_calls: {len(tool_calls or [])}",
                flush=True,
            )
            if tool_calls:
                print(f"[STREAM DEBUG] Tool calls: {tool_calls}", flush=True)

            print(
                f"[STREAM YIELD DEBUG] About to yield tool chunk",
                flush=True,
            )
            yield chunk
            print(
                f"[STREAM YIELD DEBUG] Finished yielding tool chunk",
                flush=True,
            )
        # DON'T yield final chunk if we already yielded chunks during the loop
        # (this would cause duplication since node_functions_mixin appends all chunks)

    def _create_streamer(self):
        """Create text iterator streamer.

        Returns:
            TextIteratorStreamer instance
        """
        skip_special = not self.use_mistral_native
        return TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=skip_special,
        )

    def _build_generation_kwargs(self, inputs, streamer, kwargs):
        """Build generation keyword arguments.

        Args:
            inputs: Input tensors
            streamer: Text streamer
            kwargs: Additional parameters

        Returns:
            Dictionary of generation kwargs
        """
        eos_token_id, pad_token_id = self._get_token_ids()

        stopping_criteria = [
            ExternalConditionStoppingCriteria(self.should_stop_generation)
        ]

        return {
            **inputs,
            "max_new_tokens": kwargs.get(
                "max_new_tokens", self.max_new_tokens
            ),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "top_k": kwargs.get("top_k", self.top_k),
            "repetition_penalty": kwargs.get(
                "repetition_penalty", self.repetition_penalty
            ),
            "do_sample": kwargs.get("do_sample", self.do_sample),
            "pad_token_id": pad_token_id,
            "eos_token_id": eos_token_id,
            "streamer": streamer,
            "stopping_criteria": stopping_criteria,
        }

    def _log_generation_params(self, generation_kwargs, inputs, kwargs):
        """Log generation parameters for debugging.

        Args:
            generation_kwargs: Final generation parameters
            inputs: Input tensors
            kwargs: Original kwargs
        """
        debug_msg = f"""
{'='*70}
[ADAPTER STREAM DEBUG] Generation Parameters:
  max_new_tokens FROM KWARGS: {kwargs.get('max_new_tokens', 'NOT SET')}
  max_new_tokens FALLBACK: {self.max_new_tokens}
  max_new_tokens FINAL: {generation_kwargs['max_new_tokens']}
  temperature: {generation_kwargs['temperature']}
  top_p: {generation_kwargs['top_p']}
  top_k: {generation_kwargs['top_k']}
  repetition_penalty: {generation_kwargs['repetition_penalty']}
  do_sample: {generation_kwargs['do_sample']}
  Input tokens: {inputs['input_ids'].shape[1] if 'input_ids' in inputs else 'unknown'}
  eos_token_id: {generation_kwargs['eos_token_id']}
  pad_token_id: {generation_kwargs['pad_token_id']}
  ALL KWARGS KEYS: {list(kwargs.keys())}
{'='*70}
"""
        sys.stderr.write(debug_msg)
        sys.stderr.flush()
        self.logger.warning(debug_msg)

    def _start_generation_thread(self, generation_kwargs):
        """Start generation in background thread.

        Args:
            generation_kwargs: Generation parameters

        Returns:
            Started thread object
        """
        thread = threading.Thread(
            target=self.model.generate, kwargs=generation_kwargs
        )
        thread.daemon = True
        thread.start()
        return thread

    def _stream_tokens(self, streamer, run_manager, full_response):
        """Stream tokens from streamer and accumulate response.

        Args:
            streamer: Text iterator streamer
            run_manager: Optional callback manager
            full_response: List to accumulate tokens

        Yields:
            ChatGenerationChunk objects
        """
        # Use the proper iterator protocol - don't access queue directly
        # This ensures TextIteratorStreamer handles EOS, tokenization, etc. correctly
        for text in streamer:
            if self._interrupted:
                self.logger.info("Stream interrupted - breaking immediately")
                self._clear_streamer_queue(streamer)
                break

            if not text:
                continue

            full_response.append(text)
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
            if run_manager:
                run_manager.on_llm_new_token(text, chunk=chunk)
            yield chunk

    def _clear_streamer_queue(self, streamer):
        """Clear streamer queue to unblock generation thread.

        Args:
            streamer: Text iterator streamer
        """
        try:
            while not streamer.text_queue.empty():
                streamer.text_queue.get_nowait()
        except:
            pass

    def _handle_stream_tool_calls(self, full_response, kwargs):
        """Parse and yield tool calls from streamed response.

        Args:
            full_response: List of response tokens
            kwargs: Generation parameters

        Yields:
            ChatGenerationChunk with tool calls if found
        """
        if not self.tools or not full_response:
            print(
                "[STREAM TOOL DEBUG] Skipping tool call handling - no tools or empty response",
                flush=True,
            )
            return

        response_text = "".join(full_response)
        self._log_stream_completion(response_text, kwargs)

        tool_calls = self._parse_stream_tool_calls(response_text, kwargs)

        if tool_calls:
            print(
                f"[STREAM TOOL DEBUG] Yielding tool_call_chunk with {len(tool_calls)} tool calls",
                flush=True,
            )
            chunk = self._create_tool_call_chunk(tool_calls)
            print(f"[STREAM TOOL DEBUG] Chunk created: {chunk}", flush=True)
            print(
                f"[STREAM TOOL DEBUG] Chunk.message.tool_calls: {chunk.message.tool_calls}",
                flush=True,
            )
            yield chunk
        else:
            print(
                "[STREAM TOOL DEBUG] No tool calls found after parsing",
                flush=True,
            )

    def _log_stream_completion(self, response_text, kwargs):
        """Log stream completion debug information.

        Args:
            response_text: Complete response text
            kwargs: Generation parameters
        """
        print(
            f"[CHAT ADAPTER DEBUG] Stream complete, response length: {len(response_text)} chars",
            flush=True,
        )
        print(
            f"[CHAT ADAPTER DEBUG] Response preview: {response_text[:300]}...",
            flush=True,
        )
        print(
            f"[CHAT ADAPTER DEBUG] Tool calling mode: {self.tool_calling_mode}",
            flush=True,
        )
        print(
            f"[CHAT ADAPTER DEBUG] use_json_mode: {self.use_json_mode}",
            flush=True,
        )
        print(
            f"[CHAT ADAPTER DEBUG] disable_tool_parsing: {kwargs.get('disable_tool_parsing', False)}",
            flush=True,
        )

    def _parse_stream_tool_calls(self, response_text, kwargs):
        """Parse tool calls from streamed response.

        Args:
            response_text: Complete response text
            kwargs: Generation parameters

        Returns:
            List of tool calls or None
        """
        if kwargs.get("disable_tool_parsing", False):
            return None

        if self.tool_calling_mode == "native" and self.use_mistral_native:
            tool_calls, _ = self._parse_mistral_tool_calls(response_text)
            if tool_calls:
                self.logger.debug(
                    f"Mistral native extracted {len(tool_calls)} tool call(s) from stream"
                )
            return tool_calls

        elif self.tool_calling_mode == "json" and self.use_json_mode:
            print(
                "[CHAT ADAPTER DEBUG] Calling _parse_json_mode_tool_calls...",
                flush=True,
            )
            tool_calls, _ = self._parse_json_mode_tool_calls(response_text)
            print(
                f"[CHAT ADAPTER DEBUG] Parse result: {len(tool_calls) if tool_calls else 0} tool calls",
                flush=True,
            )
            if tool_calls:
                print(
                    f"[CHAT ADAPTER DEBUG] Tool calls: {tool_calls}",
                    flush=True,
                )
                self.logger.debug(
                    f"JSON mode extracted {len(tool_calls)} tool call(s) from stream"
                )
            else:
                print(
                    "[CHAT ADAPTER DEBUG] NO TOOL CALLS FOUND in response",
                    flush=True,
                )
            return tool_calls

        else:
            tool_calls, _ = self._parse_tool_calls(response_text)
            if tool_calls:
                self.logger.debug(
                    f"ReAct extracted {len(tool_calls)} tool call(s) from stream"
                )
            return tool_calls

    def _create_tool_call_chunk(self, tool_calls):
        """Create final chunk with tool calls.

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            ChatGenerationChunk with tool calls
        """
        final_message = AIMessageChunk(
            content="", additional_kwargs={"tool_calls": tool_calls}
        )
        final_message.tool_calls = tool_calls
        return ChatGenerationChunk(message=final_message)

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
            signature = (
                call.get("name"),
                tuple(sorted(call.get("args", {}).items())),
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(call)
        if len(deduped) != len(tool_calls):
            print(
                f"[TOOL DEDUP DEBUG] Reduced tool calls from {len(tool_calls)} to {len(deduped)}",
                flush=True,
            )
        return deduped
