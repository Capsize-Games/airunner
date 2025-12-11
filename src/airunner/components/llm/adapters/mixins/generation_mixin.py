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

        # CRITICAL: Generate a stable message ID based on tool_calls for proper deduplication
        # LangGraph's add_messages reducer deduplicates by message ID - without a consistent ID,
        # the same tool call message can be added multiple times to the checkpoint state.
        message_id = None
        if tool_calls:
            # Use the first tool_call's ID as the basis for the message ID
            first_tool_id = tool_calls[0].get("id", "")
            if first_tool_id:
                message_id = f"ai-tool-{first_tool_id}"

        message = AIMessage(content=cleaned_text, tool_calls=tool_calls or [], id=message_id)
        generation = ChatGeneration(message=message)

        return ChatResult(generations=[generation])

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
        pil_images = []
        quantized = self._is_quantized_model()
        for source in image_urls:
            image = self._load_image_from_source(source)
            if image is None:
                self.logger.warning("Skipping unusable image source for vision prompt")
                continue

            # Resize large images to prevent garbage output from quantized models
            # 4-bit quantized Mistral3/Pixtral produces corrupted output for oversized images
            if quantized:
                image = self._resize_image_for_quantized_model(image, max_size=768)
            pil_images.append(image)

        if quantized and len(pil_images) > 4:
            self.logger.info(
                "Quantized vision model: capping images to first 4 to avoid token bloat"
            )
            pil_images = pil_images[:4]

        if not pil_images:
            # No valid images, fall back to text-only
            # CRITICAL: add_special_tokens=False - chat template already has BOS
            return self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                add_special_tokens=False,
            ).to(self.model.device)

        # Use processor to encode text and images together
        # The processor handles both tokenization and image preprocessing
        # CRITICAL: add_special_tokens=False because the chat template already
        # includes the BOS token (<s>). Without this, we get double <s><s>
        # which corrupts the model output.
        try:
            inputs = self.processor(
                text=prompt,
                images=pil_images,
                return_tensors="pt",
                padding=True,
                add_special_tokens=False,
            )
            # Move all tensors to model device
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            # Align floating tensors with model dtype to avoid Float/Half mismatches
            model_dtype = self._get_model_dtype()
            if model_dtype:
                for key, tensor in inputs.items():
                    if torch.is_floating_point(tensor) and tensor.dtype != model_dtype:
                        inputs[key] = tensor.to(dtype=model_dtype)

            self.logger.info(
                f"Prepared vision inputs with {len(pil_images)} image(s), "
                f"input_ids shape: {inputs['input_ids'].shape}, "
                f"pixel_values dtype: {inputs.get('pixel_values').dtype if 'pixel_values' in inputs else 'n/a'}"
            )
            return inputs
        except Exception as e:
            self.logger.error(f"Failed to prepare vision inputs: {e}")
            # Fall back to text-only
            # CRITICAL: add_special_tokens=False - chat template already has BOS
            return self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                add_special_tokens=False,
            ).to(self.model.device)

    def _resize_image_for_quantized_model(self, image, max_size: int = 768):
        """Resize image to prevent garbage output from quantized vision models.
        
        4-bit quantized Mistral3/Pixtral models produce corrupted output when
        processing images larger than approximately 640x640 pixels. This method
        resizes images to stay within safe bounds while preserving aspect ratio.
        
        Args:
            image: PIL Image to resize
            max_size: Maximum dimension (width or height) in pixels
            
        Returns:
            Resized PIL Image if needed, otherwise original image
        """
        from PIL import Image as PILImage
        
        if image.width <= max_size and image.height <= max_size:
            return image

        resized = image.copy()
        resized.thumbnail((max_size, max_size), PILImage.LANCZOS)

        self.logger.info(
            f"Resizing image from {image.size} to {resized.size} for quantized model compatibility"
        )

        return resized

    def _load_image_from_source(self, source):
        """Best-effort conversion of various image sources to PIL.Image."""
        import base64
        import io
        from pathlib import Path
        from urllib.parse import urlparse
        from urllib.request import Request, urlopen

        from PIL import Image

        if source is None:
            return None

        if isinstance(source, Image.Image):
            return source.convert("RGB")

        if isinstance(source, (bytes, bytearray)):
            return Image.open(io.BytesIO(source)).convert("RGB")

        if isinstance(source, dict):
            data_candidate = (
                source.get("data")
                or source.get("image")
                or source.get("content")
                or source.get("bytes")
            )
            path_candidate = source.get("path") or source.get("url")
            if data_candidate:
                return self._load_image_from_source(data_candidate)
            if path_candidate:
                return self._load_image_from_source(path_candidate)

        if isinstance(source, (str, Path)):
            path_str = str(source)
            if path_str.startswith("data:image"):
                try:
                    base64_data = path_str.split(",", 1)[1]
                except IndexError:
                    base64_data = path_str
                image_bytes = base64.b64decode(base64_data)
                return Image.open(io.BytesIO(image_bytes)).convert("RGB")

            parsed = urlparse(path_str)
            if parsed.scheme in {"http", "https"}:
                try:
                    req = Request(path_str, headers={"User-Agent": "Mozilla/5.0"})
                    with urlopen(req, timeout=10) as resp:
                        return Image.open(io.BytesIO(resp.read())).convert("RGB")
                except Exception as exc:
                    self.logger.error(f"Failed to download image: {exc}")
                    return None

            fs_path = Path(path_str).expanduser()
            if fs_path.exists():
                try:
                    return Image.open(fs_path).convert("RGB")
                except Exception as exc:
                    self.logger.error(f"Failed to open image file: {exc}")
                    return None

            try:
                return Image.open(io.BytesIO(base64.b64decode(path_str))).convert("RGB")
            except Exception:
                return None

        return None

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

    def _is_quantized_model(self) -> bool:
        """Check if the model is quantized (4-bit or 8-bit).
        
        Quantized vision models like Mistral3/Pixtral have issues processing
        large images, producing garbage output above ~640px.
        
        Returns:
            True if model uses quantization, False otherwise
        """
        try:
            if hasattr(self.model, "config"):
                config = self.model.config
                # Check for bitsandbytes quantization config
                if hasattr(config, "quantization_config"):
                    return True
            # Check for quantization attributes set by bitsandbytes
            if hasattr(self.model, "is_loaded_in_4bit") and self.model.is_loaded_in_4bit:
                return True
            if hasattr(self.model, "is_loaded_in_8bit") and self.model.is_loaded_in_8bit:
                return True
        except Exception:
            pass
        return False

    def _get_model_dtype(self) -> Optional[torch.dtype]:
        """Safely determine the model's floating dtype if available."""
        try:
            if hasattr(self.model, "dtype"):
                return self.model.dtype
            param = next(self.model.parameters(), None)
            if param is not None:
                return param.dtype
        except Exception:
            # Best-effort; fall back to default handling
            return None
        return None

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
                use_cache=True,  # Enable KV cache for faster generation
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

        thread = self._start_generation_thread(generation_kwargs)
        full_response = []

        # Always stream tokens in real-time for GUI responsiveness
        # We still accumulate full_response for tool parsing at the end
        has_tools = bool(self.tools)

        token_count = 0
        try:
            for chunk in self._stream_tokens(
                streamer, run_manager, full_response
            ):
                token_count += 1
                # Always yield chunks for real-time streaming
                yield chunk
        finally:
            thread.join()

        # If tools are enabled, yield a final message with tool_calls
        # This allows the workflow to detect and execute tool calls
        if has_tools:
            response_text = "".join(full_response)
            
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
            "use_cache": True,  # Enable KV cache for faster generation
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
                self.logger.debug("Starting model.generate() in background thread")
                self.model.generate(**generation_kwargs)
                self.logger.debug("model.generate() completed successfully")
            except Exception as e:
                self.logger.error(f"Generation thread error: {type(e).__name__}: {e}")
                import traceback
                self.logger.error(f"Generation thread traceback:\n{traceback.format_exc()}")
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
        token_count = 0
        for text in streamer:
            if self._interrupted:
                self.logger.info("Stream interrupted - breaking immediately")
                self._clear_streamer_queue(streamer)
                break

            if not text:
                continue

            token_count += 1
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
        import json
        seen = set()
        deduped = []
        for call in tool_calls:
            # Use JSON serialization to create a hashable signature
            # This handles nested lists/dicts in args that can't be directly hashed
            try:
                args_str = json.dumps(call.get("args", {}), sort_keys=True)
                signature = (call.get("name"), args_str)
            except (TypeError, ValueError):
                # If JSON serialization fails, use repr as fallback
                signature = (call.get("name"), repr(call.get("args", {})))
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(call)
        return deduped
