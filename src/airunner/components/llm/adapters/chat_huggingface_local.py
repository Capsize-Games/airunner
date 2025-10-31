"""Custom LangChain adapter for locally-loaded HuggingFace models."""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Iterator,
    Sequence,
    Union,
)
import logging
import threading
import json
import re
import uuid
import os

import torch
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.runnables import Runnable
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import (
    ChatGeneration,
    ChatGenerationChunk,
    ChatResult,
)
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from transformers.generation.streamers import TextIteratorStreamer
from airunner.components.llm.managers.external_condition_stopping_criteria import (
    ExternalConditionStoppingCriteria,
)

# Mistral native function calling support
try:
    from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
    from mistral_common.protocol.instruct.tool_calls import Function, Tool
    from mistral_common.protocol.instruct.messages import (
        UserMessage,
        AssistantMessage,
        SystemMessage as MistralSystemMessage,
    )
    from mistral_common.protocol.instruct.request import ChatCompletionRequest

    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    MistralTokenizer = None


class ChatHuggingFaceLocal(BaseChatModel):
    """
    LangChain ChatModel adapter for locally-loaded HuggingFace models.

    This adapter wraps a pre-loaded HuggingFace model and tokenizer,
    allowing them to work with LangChain's agent system.

    Attributes:
        model: The loaded HuggingFace model
        tokenizer: The loaded HuggingFace tokenizer
        max_new_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        repetition_penalty: Penalty for repeating tokens
        do_sample: Whether to use sampling
    """

    model: Any
    tokenizer: Any
    model_path: Optional[str] = None
    use_mistral_native: bool = False  # Use Mistral native function calling
    use_json_mode: bool = False  # Use structured JSON output for tool calling
    tool_calling_mode: str = "react"  # "native", "json", or "react"
    max_new_tokens: int = (
        4096  # INCREASED from 512 for complex reasoning tasks
    )
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.15
    do_sample: bool = True
    tools: Optional[List[Any]] = None  # Bound tools
    _interrupted: bool = False  # Interrupt flag
    _mistral_tokenizer: Optional[Any] = None  # Mistral native tokenizer

    class Config:
        arbitrary_types_allowed = True

    def model_post_init(self, __context: Any) -> None:
        """Called after Pydantic model initialization."""
        # Auto-detect tool calling capability
        self._detect_tool_calling_mode()

        # Initialize Mistral tokenizer if using native mode
        if self.use_mistral_native and self.tool_calling_mode == "native":
            self._init_mistral_tokenizer()

    def _detect_tool_calling_mode(self) -> None:
        """
        Auto-detect which tool calling mode to use based on model.

        Priority:
        1. Native (Mistral with tekken.json) - best reliability
        2. Structured JSON (Qwen, Llama-3.1, Phi-3) - good reliability
        3. ReAct (fallback for all models) - okay reliability
        """
        if not self.model_path:
            self.tool_calling_mode = "react"
            return

        model_path_lower = self.model_path.lower()

        # Check for Mistral with tekken.json (native support)
        tekken_path = os.path.join(self.model_path, "tekken.json")
        if os.path.exists(tekken_path) and "mistral" in model_path_lower:
            self.tool_calling_mode = "native"
            self.use_mistral_native = True
            return

        # For all other models, use ReAct pattern
        # LangChain's standard tool calling via bind_tools() works for most models
        # including Qwen, Llama, etc. - no need for custom JSON parsing
        self.tool_calling_mode = "react"
        print(
            f"ℹ Using LangChain standard tool calling (model: {self.model_path})"
        )

    @property
    def logger(self):
        """Lazy logger initialization."""
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger(__name__)
        return self._logger

    def set_interrupted(self, value: bool) -> None:
        """Set interrupt flag to stop generation."""
        self._interrupted = value
        if value:
            self.logger.info(f"ChatModel interrupt flag set to {value}")

    def should_stop_generation(self) -> bool:
        """Check if generation should be interrupted."""
        if self._interrupted:
            self.logger.info(
                "should_stop_generation returning True - interrupting!"
            )
        return self._interrupted

    @property
    def _llm_type(self) -> str:
        """Return type of language model."""
        return "huggingface_local"

    def _init_mistral_tokenizer(self) -> None:
        """Initialize Mistral native tokenizer if available."""
        if not MISTRAL_AVAILABLE:
            print("Mistral common library not available")
            return

        if not self.model_path:
            print("No model path provided for Mistral tokenizer")
            return

        tekken_path = os.path.join(self.model_path, "tekken.json")
        if not os.path.exists(tekken_path):
            print(f"tekken.json not found at {tekken_path}")
            return

        # Check if the HuggingFace tokenizer has Mistral's function calling tokens
        # If it's using LlamaTokenizer with only basic tokens, native function calling won't work
        if hasattr(self.tokenizer, "all_special_tokens"):
            special_tokens = self.tokenizer.all_special_tokens
            # Mistral models should have tool-specific tokens
            has_tool_tokens = any(
                "tool" in str(token).lower() for token in special_tokens
            )
            if not has_tool_tokens and len(special_tokens) < 10:
                print(
                    f"⚠ Mistral native function calling NOT supported by this model:"
                )
                print(
                    f"   → Uses {type(self.tokenizer).__name__} with only {len(special_tokens)} special tokens"
                )
                print(
                    f"   → Needs Mistral V3-Tekken tokenizer with function calling tokens"
                )
                print(
                    f"   → Quantized models often lose native function calling capability"
                )
                print(f"   → Falling back to prompt-based tool calling")
                self.use_mistral_native = False
                return

        try:
            self._mistral_tokenizer = MistralTokenizer.from_file(tekken_path)
            self.use_mistral_native = True
            print(
                f"✓ Mistral native function calling ENABLED for model at {self.model_path}"
            )
        except Exception as e:
            print(f"Failed to load Mistral tokenizer: {e}")
            self.use_mistral_native = False

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, Callable, BaseTool]],
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind tools to this chat model.

        For Ministral models with native function calling support, we use
        the Mistral tokenizer and native tool format. For other models,
        we inject tool schemas into the system prompt and parse responses.

        Args:
            tools: List of tools to bind (LangChain tools or callables)
            **kwargs: Additional arguments

        Returns:
            New instance with tools bound
        """
        # Convert tools to OpenAI format for consistency
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]

        # Create new instance with tools
        return self.__class__(
            model=self.model,
            tokenizer=self.tokenizer,
            model_path=self.model_path,
            use_mistral_native=self.use_mistral_native,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            repetition_penalty=self.repetition_penalty,
            do_sample=self.do_sample,
            tools=formatted_tools,
            _mistral_tokenizer=self._mistral_tokenizer,
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages."""
        # Convert messages to prompt (text or tokens)
        prompt = self._messages_to_prompt(messages)

        # Handle Mistral native tokens vs regular text prompt
        if isinstance(prompt, list):
            # Mistral native: prompt is already tokenized
            inputs = {
                "input_ids": torch.tensor([prompt]).to(self.model.device)
            }
        else:
            # Regular tokenization
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            ).to(self.model.device)

        # Generate
        # Determine token IDs
        if self.use_mistral_native and self._mistral_tokenizer:
            eos_token_id = (
                self._mistral_tokenizer.instruct_tokenizer.tokenizer.eos_id
            )
            pad_token_id = eos_token_id
        elif self.tokenizer:
            eos_token_id = self.tokenizer.eos_token_id
            pad_token_id = self.tokenizer.eos_token_id
        else:
            # Fallback for models without tokenizer (shouldn't happen)
            eos_token_id = 2
            pad_token_id = 2

        with torch.no_grad():
            outputs = self.model.generate(
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

        # Decode only the new tokens (skip the input prompt)
        input_length = inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_length:]

        # Decode using appropriate tokenizer
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

        # Parse tool calls if tools are bound
        tool_calls = None

        # Check if tool parsing is disabled (for conversational responses after tools)
        disable_tool_parsing = kwargs.get("disable_tool_parsing", False)

        if self.tools and not disable_tool_parsing:
            if self.tool_calling_mode == "native" and self.use_mistral_native:
                tool_calls, response_text = self._parse_mistral_tool_calls(
                    response_text
                )
                if tool_calls:
                    self.logger.debug(
                        f"Mistral native extracted {len(tool_calls)} tool call(s)"
                    )
            elif self.tool_calling_mode == "json" and self.use_json_mode:
                tool_calls, response_text = self._parse_json_mode_tool_calls(
                    response_text
                )
                if tool_calls:
                    self.logger.debug(
                        f"JSON mode extracted {len(tool_calls)} tool call(s)"
                    )
            else:
                # ReAct pattern fallback
                tool_calls, response_text = self._parse_tool_calls(
                    response_text
                )
                if tool_calls:
                    self.logger.debug(
                        f"ReAct extracted {len(tool_calls)} tool call(s)"
                    )

        # Create chat generation
        message = AIMessage(content=response_text, tool_calls=tool_calls or [])
        generation = ChatGeneration(message=message)

        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream response from messages using a HuggingFace streamer."""
        prompt = self._messages_to_prompt(messages)

        # Handle Mistral native tokens vs regular text prompt
        if isinstance(prompt, list):
            # Mistral native: prompt is already tokenized
            inputs = {
                "input_ids": torch.tensor([prompt]).to(self.model.device)
            }
            self.logger.debug(
                f"Using Mistral native tokenization with {len(prompt)} tokens"
            )
        else:
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            ).to(self.model.device)

        # Use appropriate tokenizer for streamer
        # Note: TextIteratorStreamer needs the HuggingFace tokenizer, not Mistral tokenizer
        # The Mistral tokenizer is only for encoding the prompt with tools
        # Only keep special tokens for Mistral native function calling
        skip_special = not self.use_mistral_native
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=skip_special,
        )

        # Reset interrupt flag before generation
        self._interrupted = False

        # Create stopping criteria for interrupt handling
        stopping_criteria = [
            ExternalConditionStoppingCriteria(self.should_stop_generation)
        ]

        # Determine token IDs for streaming
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

        generation_kwargs = {
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

        # DEBUG: Log ALL generation parameters to STDERR and logger
        import sys

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
  eos_token_id: {eos_token_id}
  pad_token_id: {pad_token_id}
  ALL KWARGS KEYS: {list(kwargs.keys())}
{'='*70}
"""
        sys.stderr.write(debug_msg)
        sys.stderr.flush()
        self.logger.warning(debug_msg)  # Use warning level to ensure it shows

        thread = threading.Thread(
            target=self.model.generate, kwargs=generation_kwargs
        )
        thread.daemon = True  # Allow thread to be killed when interrupted
        thread.start()

        # Accumulate full response for tool call parsing (needed for Mistral native)
        full_response = []

        try:
            for text in streamer:
                # CRITICAL: Check interrupt BEFORE processing token
                # This is the ONLY place the interrupt can actually work
                # because the model.generate() thread doesn't check stopping_criteria
                if self._interrupted:
                    self.logger.info(
                        "Stream interrupted - breaking immediately"
                    )
                    # Clear the streamer queue to unblock the generation thread
                    try:
                        while not streamer.text_queue.empty():
                            streamer.text_queue.get_nowait()
                    except:
                        pass
                    break

                if not text:
                    continue
                full_response.append(text)
                chunk = ChatGenerationChunk(
                    message=AIMessageChunk(content=text)
                )
                if run_manager:
                    run_manager.on_llm_new_token(text, chunk=chunk)
                yield chunk
        finally:
            thread.join()

        # After streaming completes, parse for tool calls based on mode
        if self.tools and full_response:
            response_text = "".join(full_response)
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

            # Check if tool parsing is disabled (for conversational responses after tools)
            disable_tool_parsing = kwargs.get("disable_tool_parsing", False)
            print(
                f"[CHAT ADAPTER DEBUG] disable_tool_parsing: {disable_tool_parsing}",
                flush=True,
            )

            tool_calls = None

            if (
                not disable_tool_parsing
                and self.tool_calling_mode == "native"
                and self.use_mistral_native
            ):
                tool_calls, _ = self._parse_mistral_tool_calls(response_text)
                if tool_calls:
                    self.logger.debug(
                        f"Mistral native extracted {len(tool_calls)} tool call(s) from stream"
                    )
            elif (
                not disable_tool_parsing
                and self.tool_calling_mode == "json"
                and self.use_json_mode
            ):
                print(
                    f"[CHAT ADAPTER DEBUG] Calling _parse_json_mode_tool_calls...",
                    flush=True,
                )
                tool_calls, cleaned_text = self._parse_json_mode_tool_calls(
                    response_text
                )
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
                        f"[CHAT ADAPTER DEBUG] NO TOOL CALLS FOUND in response",
                        flush=True,
                    )
            else:
                # ReAct pattern fallback
                tool_calls, cleaned_text = self._parse_tool_calls(
                    response_text
                )
                if tool_calls:
                    self.logger.debug(
                        f"ReAct extracted {len(tool_calls)} tool call(s) from stream"
                    )

            # If tool calls found, yield a final chunk with tool_calls
            if tool_calls:
                # Create AIMessageChunk with tool_calls properly set
                # Set as direct attribute (LangChain AIMessageChunk pattern)
                final_message = AIMessageChunk(
                    content="", additional_kwargs={"tool_calls": tool_calls}
                )
                final_message.tool_calls = tool_calls
                final_chunk = ChatGenerationChunk(message=final_message)
                yield final_chunk

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert LangChain messages to prompt text.

        For Mistral native mode, this returns tokens as a string representation.
        For standard mode, it uses the tokenizer's chat template or fallback.
        """
        # Mistral native function calling
        if self.use_mistral_native and self._mistral_tokenizer and self.tools:
            return self._messages_to_mistral_tokens(messages)

        # Mistral3 models without HF tokenizer - must use mistral_common
        if not self.tokenizer and self.model_path:
            # Initialize Mistral tokenizer if not already done
            if not self._mistral_tokenizer:
                self._init_mistral_tokenizer()

            if self._mistral_tokenizer:
                # Use Mistral native formatting
                return self._messages_to_mistral_tokens(messages)
            else:
                raise ValueError(
                    "No tokenizer available for Mistral3 model. "
                    "Ensure mistral_common is installed and tekken.json exists."
                )

        # Use tokenizer's chat template if available
        if self.tokenizer and hasattr(self.tokenizer, "apply_chat_template"):
            # Convert to format expected by chat template
            chat_messages = []
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    chat_messages.append(
                        {"role": "system", "content": msg.content}
                    )
                elif isinstance(msg, HumanMessage):
                    chat_messages.append(
                        {"role": "user", "content": msg.content}
                    )
                elif isinstance(msg, AIMessage):
                    chat_messages.append(
                        {"role": "assistant", "content": msg.content}
                    )

            return self.tokenizer.apply_chat_template(
                chat_messages, tokenize=False, add_generation_prompt=True
            )

        # Fallback: simple concatenation
        prompt_parts = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                prompt_parts.append(f"System: {msg.content}")
            elif isinstance(msg, HumanMessage):
                prompt_parts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                prompt_parts.append(f"Assistant: {msg.content}")

        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)

    def _messages_to_mistral_tokens(
        self, messages: List[BaseMessage]
    ) -> List[int]:
        """Convert messages to Mistral tokens using native function calling format."""
        # Convert LangChain tools to Mistral Tool format
        mistral_tools = []
        for tool in self.tools:
            mistral_tools.append(
                Tool(
                    function=Function(
                        name=tool["function"]["name"],
                        description=tool["function"]["description"],
                        parameters=tool["function"].get("parameters", {}),
                    )
                )
            )

        self.logger.debug(f"Encoding {len(mistral_tools)} tools for Mistral")

        # Convert messages to Mistral format
        mistral_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                mistral_messages.append(
                    MistralSystemMessage(content=msg.content)
                )
            elif isinstance(msg, HumanMessage):
                mistral_messages.append(UserMessage(content=msg.content))
            elif isinstance(msg, AIMessage):
                mistral_messages.append(AssistantMessage(content=msg.content))

        self.logger.debug(
            f"Converting {len(mistral_messages)} messages to Mistral format"
        )

        # Create completion request
        completion_request = ChatCompletionRequest(
            tools=mistral_tools, messages=mistral_messages
        )

        # Encode using Mistral tokenizer
        tokens = self._mistral_tokenizer.encode_chat_completion(
            completion_request
        ).tokens

        self.logger.debug(f"Encoded to {len(tokens)} tokens")
        return tokens
        mistral_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                mistral_messages.append(
                    MistralSystemMessage(content=msg.content)
                )
            elif isinstance(msg, HumanMessage):
                mistral_messages.append(UserMessage(content=msg.content))
            elif isinstance(msg, AIMessage):
                mistral_messages.append(AssistantMessage(content=msg.content))

        # Create completion request
        completion_request = ChatCompletionRequest(
            tools=mistral_tools, messages=mistral_messages
        )

        # Encode using Mistral tokenizer
        tokens = self._mistral_tokenizer.encode_chat_completion(
            completion_request
        ).tokens

        return tokens

    def get_tool_schemas_text(self) -> str:
        """Get tool schemas as formatted text for system prompt.

        This should be called by the workflow manager to add tool descriptions
        to the system prompt, rather than injecting into message history.

        For Mistral native mode, tools are encoded in the tokenization,
        so we return empty string to avoid duplicate tool descriptions.

        Returns:
            Formatted tool descriptions or empty string if no tools bound or using native
        """
        # Don't add tool schemas to system prompt when using Mistral native
        if self.use_mistral_native:
            return ""

        return self._format_tools_for_prompt() if self.tools else ""

    def _format_tools_for_prompt(self) -> str:
        """Format tools as text for the system prompt."""
        if not self.tools:
            return ""

        tool_strings = []
        for tool in self.tools:
            tool_str = f"- {tool['function']['name']}: {tool['function']['description']}"

            # Add parameter info
            params = (
                tool["function"].get("parameters", {}).get("properties", {})
            )
            if params:
                param_strs = []
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "string")
                    param_desc = param_info.get("description", "")
                    param_strs.append(
                        f"  - {param_name} ({param_type}): {param_desc}"
                    )
                tool_str += "\n" + "\n".join(param_strs)

            tool_strings.append(tool_str)

        tools_text = "\n\n".join(tool_strings)

        # Build the instructions without f-string to avoid format specifier issues
        instructions = "## IMPORTANT: Tool Usage Instructions\n\n"
        instructions += (
            "You have access to the following tools to help users:\n\n"
        )
        instructions += tools_text
        instructions += "\n\n**How to use a tool:**\n\n"
        instructions += "When you need to use a tool, respond with ONLY a JSON code block in this format:\n\n"
        instructions += '```json\n{\n    "tool": "tool_name",\n    "arguments": {\n        "param_name": "value"\n    }\n}\n```\n\n'
        instructions += '**Example:** If user asks "generate an image of a sunset", respond:\n'
        instructions += '```json\n{\n    "tool": "generate_image",\n    "arguments": {\n        "prompt": "sunset over ocean with orange and pink sky"\n    }\n}\n```\n\n'
        instructions += "Do NOT add any other text when calling a tool - just the JSON block. After the tool executes, you will receive the result and can then provide a response to the user."

        return instructions

    def _parse_mistral_tool_calls(
        self, response_text: str
    ) -> tuple[Optional[List[dict]], str]:
        """Parse tool calls from Mistral native format.

        Mistral models output tool calls in a specific format that we need to parse.

        Args:
            response_text: The model's response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        tool_calls = []

        # Mistral tool call pattern: [TOOL_CALLS] [{"name": "...", "arguments": {...}}]
        tool_call_pattern = r"\[TOOL_CALLS\]\s*(\[.*?\])"
        matches = re.findall(tool_call_pattern, response_text, re.DOTALL)

        for match in matches:
            try:
                calls = json.loads(match)
                for call in calls:
                    if isinstance(call, dict) and "name" in call:
                        tool_calls.append(
                            {
                                "name": call["name"],
                                "args": call.get("arguments", {}),
                                "id": call.get("id", str(uuid.uuid4())),
                            }
                        )
            except json.JSONDecodeError:
                continue

        # Remove tool call markers from response text
        cleaned_text = re.sub(
            tool_call_pattern, "", response_text, flags=re.DOTALL
        )
        cleaned_text = cleaned_text.strip()

        return (tool_calls if tool_calls else None, cleaned_text)

    def _parse_json_mode_tool_calls(
        self, response_text: str
    ) -> tuple[Optional[List[dict]], str]:
        """Parse tool calls from structured JSON mode output.

        For models like Qwen2.5, Llama-3.1, Phi-3 that can output clean JSON.
        Expected format: {"tool": "tool_name", "arguments": {...}}

        Args:
            response_text: The model's response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        print(
            f"[JSON PARSE DEBUG] Parsing response of length {len(response_text)}",
            flush=True,
        )
        print(
            f"[JSON PARSE DEBUG] First 500 chars: {response_text[:500]}",
            flush=True,
        )

        tool_calls = []
        cleaned_text = response_text

        # Quick fix for models that use single quotes instead of double quotes in JSON
        # This is technically invalid JSON but common in model outputs
        if "{'tool'" in response_text or '{"tool":' not in response_text:
            print(
                f"[JSON PARSE DEBUG] Attempting to fix single-quote JSON...",
                flush=True,
            )
            # Simple heuristic: if we see Python-style single quotes around strings, try to fix
            # This won't handle all cases but helps with common patterns
            response_text_fixed = (
                response_text.replace("':", '":')
                .replace(": '", ': "')
                .replace("', '", '", "')
                .replace("'}", '"}')
            )
            if response_text_fixed != response_text:
                print(
                    f"[JSON PARSE DEBUG] Fixed some single quotes, retrying parse...",
                    flush=True,
                )
                response_text = response_text_fixed

        # Try parsing entire response as JSON first (most reliable)
        try:
            print(
                f"[JSON PARSE DEBUG] Attempting to parse entire response as JSON...",
                flush=True,
            )
            data = json.loads(response_text.strip())
            if isinstance(data, dict) and ("tool" in data or "name" in data):
                tool_name = data.get("tool") or data.get("name")
                tool_args = data.get("arguments", {})

                tool_calls.append(
                    {
                        "name": tool_name,
                        "args": tool_args,
                        "id": str(uuid.uuid4()),
                    }
                )
                print(
                    f"[JSON PARSE DEBUG] ✓ Parsed entire response as JSON tool call: {tool_name}",
                    flush=True,
                )
                self.logger.debug(f"Parsed JSON tool call: {tool_name}")
                cleaned_text = ""  # Tool call was entire response
                return (tool_calls, cleaned_text)
            elif isinstance(data, list):
                # Handle array of tool calls
                print(
                    f"[JSON PARSE DEBUG] Response is JSON array with {len(data)} items",
                    flush=True,
                )
                for item in data:
                    if isinstance(item, dict) and (
                        "tool" in item or "name" in item
                    ):
                        tool_name = item.get("tool") or item.get("name")
                        tool_args = item.get("arguments", {})
                        tool_calls.append(
                            {
                                "name": tool_name,
                                "args": tool_args,
                                "id": str(uuid.uuid4()),
                            }
                        )
                if tool_calls:
                    print(
                        f"[JSON PARSE DEBUG] ✓ Parsed {len(tool_calls)} tool calls from array",
                        flush=True,
                    )
                    return (tool_calls, "")
        except json.JSONDecodeError as e:
            print(f"[JSON PARSE DEBUG] JSON parse failed: {e}", flush=True)

            # FALLBACK: Try Python literal_eval for Python-style dicts with single quotes
            print(
                f"[JSON PARSE DEBUG] Attempting Python ast.literal_eval fallback...",
                flush=True,
            )
            try:
                import ast

                data = ast.literal_eval(response_text.strip())
                if isinstance(data, dict) and (
                    "tool" in data or "name" in data
                ):
                    tool_name = data.get("tool") or data.get("name")
                    tool_args = data.get("arguments", {})

                    tool_calls.append(
                        {
                            "name": tool_name,
                            "args": tool_args,
                            "id": str(uuid.uuid4()),
                        }
                    )
                    print(
                        f"[JSON PARSE DEBUG] ✓ Parsed Python-style dict as tool call: {tool_name}",
                        flush=True,
                    )
                    self.logger.debug(
                        f"Parsed Python dict tool call: {tool_name}"
                    )
                    cleaned_text = ""  # Tool call was entire response
                    return (tool_calls, cleaned_text)
            except (ValueError, SyntaxError) as ast_error:
                print(
                    f"[JSON PARSE DEBUG] Python literal_eval also failed: {ast_error}",
                    flush=True,
                )

            # Try parsing multiple JSON objects separated by commas (invalid JSON but common model output)
            print(
                f"[JSON PARSE DEBUG] Attempting to split by commas and parse individually...",
                flush=True,
            )
            # Split on "}, {" pattern to separate multiple objects
            if "}, {" in response_text:
                parts = response_text.split("}, {")
                print(
                    f"[JSON PARSE DEBUG] Found {len(parts)} potential JSON objects",
                    flush=True,
                )
                for i, part in enumerate(parts):
                    # Reconstruct valid JSON by adding back the braces
                    if i > 0:
                        part = "{" + part
                    if i < len(parts) - 1:
                        part = part + "}"
                    try:
                        data = json.loads(part.strip())
                        if isinstance(data, dict) and (
                            "tool" in data or "name" in data
                        ):
                            tool_name = data.get("tool") or data.get("name")
                            tool_args = data.get("arguments", {})
                            tool_calls.append(
                                {
                                    "name": tool_name,
                                    "args": tool_args,
                                    "id": str(uuid.uuid4()),
                                }
                            )
                            print(
                                f"[JSON PARSE DEBUG] ✓ Parsed object {i+1}: {tool_name}",
                                flush=True,
                            )
                    except json.JSONDecodeError as e2:
                        print(
                            f"[JSON PARSE DEBUG] Failed to parse part {i+1}: {e2}",
                            flush=True,
                        )
                        continue
                if tool_calls:
                    print(
                        f"[JSON PARSE DEBUG] ✓ Parsed {len(tool_calls)} tool calls from comma-separated objects",
                        flush=True,
                    )
                    return (tool_calls, "")

        # Try extracting JSON from code blocks: ```json {...} ```
        json_block_pattern = r"```json\s*(\{[^`]+\})\s*```"
        matches = re.findall(json_block_pattern, response_text, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                if "tool" in data or "name" in data:
                    tool_name = data.get("tool") or data.get("name")
                    tool_args = data.get("arguments", {})

                    tool_calls.append(
                        {
                            "name": tool_name,
                            "args": tool_args,
                            "id": str(uuid.uuid4()),
                        }
                    )
                    print(f"✓ Parsed JSON block tool call: {tool_name}")
            except json.JSONDecodeError as e:
                print(f"⚠ Failed to parse JSON block: {e}")
                continue

        # Remove JSON blocks from response
        cleaned_text = re.sub(
            json_block_pattern, "", response_text, flags=re.DOTALL
        )

        # Try extracting JSON from anywhere in text (handles nested objects)
        if not tool_calls:
            # Match JSON objects that contain "tool" or "name" key
            # This regex handles nested braces by matching balanced JSON structures
            json_pattern = r'\{(?:[^{}]|(\{(?:[^{}]|\{[^{}]*\})*\}))*(?:"tool"|"name")(?:[^{}]|(\{(?:[^{}]|\{[^{}]*\})*\}))*\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)

            # The pattern captures groups, but we want the full match
            # So we need to search instead of findall
            for match in re.finditer(json_pattern, response_text, re.DOTALL):
                json_str = match.group(0)
                try:
                    data = json.loads(json_str)
                    if "tool" in data or "name" in data:
                        tool_name = data.get("tool") or data.get("name")
                        tool_args = data.get("arguments", {})

                        tool_calls.append(
                            {
                                "name": tool_name,
                                "args": tool_args,
                                "id": str(uuid.uuid4()),
                            }
                        )
                        self.logger.debug(
                            f"Parsed embedded JSON tool call: {tool_name}"
                        )
                        cleaned_text = cleaned_text.replace(
                            json_str, ""
                        ).strip()
                except json.JSONDecodeError:
                    continue

        cleaned_text = cleaned_text.strip()
        return (tool_calls if tool_calls else None, cleaned_text)

    def parse_tool_calls_from_response(
        self, response_text: str
    ) -> tuple[Optional[List[dict]], str]:
        """Parse tool calls using the appropriate mode-specific parser.

        This is the public method that the workflow should call.
        It dispatches to the correct parser based on tool_calling_mode.

        Args:
            response_text: The complete model response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        if not self.tools:
            return (None, response_text)

        if self.tool_calling_mode == "native" and self.use_mistral_native:
            return self._parse_mistral_tool_calls(response_text)
        elif self.tool_calling_mode == "json" and self.use_json_mode:
            return self._parse_json_mode_tool_calls(response_text)
        else:
            # ReAct pattern fallback
            return self._parse_tool_calls(response_text)

    def _parse_tool_calls(
        self, response_text: str
    ) -> tuple[Optional[List[dict]], str]:
        """Parse tool calls from model response (ReAct fallback format).

        Args:
            response_text: The model's response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        tool_calls = []

        # Look for JSON blocks with tool calls
        json_pattern = r"```json\s*(\{[^`]+\})\s*```"
        matches = re.findall(json_pattern, response_text, re.DOTALL)

        for match in matches:
            try:
                tool_data = json.loads(match)
                if "tool" in tool_data or "name" in tool_data:
                    tool_name = tool_data.get("tool") or tool_data.get("name")
                    tool_args = tool_data.get("arguments", {})

                    # LangChain tool_call format
                    tool_calls.append(
                        {
                            "name": tool_name,
                            "args": tool_args,
                            "id": str(uuid.uuid4()),
                        }
                    )
            except json.JSONDecodeError:
                continue

        # Remove JSON blocks from response text
        cleaned_text = re.sub(json_pattern, "", response_text, flags=re.DOTALL)
        cleaned_text = cleaned_text.strip()

        return (tool_calls if tool_calls else None, cleaned_text)
