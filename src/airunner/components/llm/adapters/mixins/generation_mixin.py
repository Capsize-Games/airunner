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
            # Get max length from model config, default to 131072 for modern LLMs
            max_length = getattr(self.model.config, "max_position_embeddings", 131072)
            return self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=max_length,
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
        self.logger.debug("[STREAM DEBUG] _stream() called")
        prompt = self._messages_to_prompt(messages)
        self.logger.debug(f"[STREAM DEBUG] Prompt length: {len(prompt)}")
        inputs = self._prepare_inputs(prompt)

        streamer = self._create_streamer()
        self._interrupted = False

        generation_kwargs = self._build_generation_kwargs(
            inputs, streamer, kwargs
        )

        thread = self._start_generation_thread(generation_kwargs)
        full_response = []

        # Always stream tokens in real-time for GUI responsiveness
        # We still accumulate full_response for tool parsing at the end
        has_tools = bool(self.tools)
        self.logger.debug(f"[STREAM DEBUG] has_tools={has_tools}, tools={len(self.tools) if self.tools else 0}")

        token_count = 0
        try:
            for chunk in self._stream_tokens(
                streamer, run_manager, full_response
            ):
                token_count += 1
                # Always yield chunks for real-time streaming
                yield chunk
        finally:
            self.logger.debug(f"[STREAM DEBUG] Joining thread, token_count={token_count}")
            thread.join()
            self.logger.debug("[STREAM DEBUG] Thread joined")

        # If tools are enabled, yield a final message with tool_calls
        # This allows the workflow to detect and execute tool calls
        if has_tools:
            response_text = "".join(full_response)
            self.logger.debug(f"[STREAM DEBUG] Full response length: {len(response_text)}")
            
            # Parse tool calls and get cleaned text
            tool_calls = self._parse_stream_tool_calls(response_text, kwargs)
            _, cleaned_text = self._parse_tool_calls_if_enabled(
                response_text, kwargs
            )

            if tool_calls:
                tool_calls = self._deduplicate_tool_calls(tool_calls)
                # Only yield final message with tool_calls if we found any
                # Use empty content since we already streamed the text
                message = AIMessageChunk(
                    content="", tool_calls=tool_calls
                )
                chunk = ChatGenerationChunk(message=message)
                self.logger.debug(f"[STREAM DEBUG] Yielding tool_calls chunk with {len(tool_calls)} tool calls")
                yield chunk

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

    def _start_generation_thread(self, generation_kwargs):
        """Start generation in background thread.

        Args:
            generation_kwargs: Generation parameters

        Returns:
            Started thread object
        """
        def _generate_with_error_handling():
            try:
                self.logger.debug("[STREAM DEBUG] Generation thread starting")
                self.model.generate(**generation_kwargs)
                self.logger.debug("[STREAM DEBUG] Generation thread completed")
            except Exception as e:
                self.logger.error(f"[STREAM DEBUG] Generation thread error: {e}", exc_info=True)
                # Signal the streamer that generation failed
                if "streamer" in generation_kwargs:
                    try:
                        generation_kwargs["streamer"].text_queue.put(None)
                    except:
                        pass
        
        thread = threading.Thread(target=_generate_with_error_handling)
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
        self.logger.debug("[STREAM DEBUG] Starting to iterate over streamer")
        token_count = 0
        for text in streamer:
            if self._interrupted:
                self.logger.info("Stream interrupted - breaking immediately")
                self._clear_streamer_queue(streamer)
                break

            if not text:
                continue

            token_count += 1
            if token_count <= 5 or token_count % 50 == 0:
                self.logger.debug(f"[STREAM DEBUG] Token {token_count}: '{text[:30]}...'")
            full_response.append(text)
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
            if run_manager:
                run_manager.on_llm_new_token(text, chunk=chunk)
            yield chunk
        
        self.logger.debug(f"[STREAM DEBUG] Streamer iteration complete, total tokens: {token_count}")

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
            return

        response_text = "".join(full_response)

        tool_calls = self._parse_stream_tool_calls(response_text, kwargs)

        if tool_calls:
            chunk = self._create_tool_call_chunk(tool_calls)
            yield chunk

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
            tool_calls, _ = self._parse_json_mode_tool_calls(response_text)
            if tool_calls:
                self.logger.debug(
                    f"JSON mode extracted {len(tool_calls)} tool call(s) from stream"
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
        return deduped
