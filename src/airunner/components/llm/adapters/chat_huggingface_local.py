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
from langchain_core.runnables import Runnable, RunnableConfig
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
    model_path: Optional[str] = None  # Path to model directory
    use_mistral_native: bool = False  # Use Mistral native function calling
    max_new_tokens: int = 500
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

    @property
    def logger(self):
        """Lazy logger initialization."""
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger(__name__)
        return self._logger

    def set_interrupted(self, value: bool) -> None:
        """Set interrupt flag to stop generation."""
        self._interrupted = value

    def should_stop_generation(self) -> bool:
        """Check if generation should be interrupted."""
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
            print(f"[DEBUG] Mistral raw response: {response_text[:500]}")
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
        if self.tools:
            if self.use_mistral_native:
                print(
                    f"[DEBUG] Parsing Mistral tool calls from response: {response_text[:200]}"
                )
                tool_calls, response_text = self._parse_mistral_tool_calls(
                    response_text
                )
                print(f"[DEBUG] Extracted tool_calls: {tool_calls}")
                print(f"[DEBUG] Cleaned response text: {response_text[:200]}")
            else:
                tool_calls, response_text = self._parse_tool_calls(
                    response_text
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
            print(
                f"[DEBUG] Using Mistral native tokenization with {len(prompt)} tokens"
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

        thread = threading.Thread(
            target=self.model.generate, kwargs=generation_kwargs
        )
        thread.start()

        # Accumulate full response for tool call parsing (needed for Mistral native)
        full_response = []

        try:
            for text in streamer:
                if self._interrupted:
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

        # After streaming completes, parse for tool calls if using Mistral native
        if self.tools and self.use_mistral_native and full_response:
            response_text = "".join(full_response)
            print(
                f"[DEBUG] Mistral full streamed response: {response_text[:500]}"
            )
            tool_calls, _ = self._parse_mistral_tool_calls(response_text)
            print(f"[DEBUG] Extracted tool_calls from stream: {tool_calls}")

            # If tool calls found, yield a final chunk with tool_calls
            if tool_calls:
                final_chunk = ChatGenerationChunk(
                    message=AIMessageChunk(content="", tool_calls=tool_calls)
                )
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

        print(f"[DEBUG] Encoding {len(mistral_tools)} tools for Mistral")
        if mistral_tools:
            print(f"[DEBUG] First tool: {mistral_tools[0].function.name}")

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

        print(
            f"[DEBUG] Converting {len(mistral_messages)} messages to Mistral format"
        )
        print(f"[DEBUG] Last message: {mistral_messages[-1].content[:100]}")

        # Create completion request
        completion_request = ChatCompletionRequest(
            tools=mistral_tools, messages=mistral_messages
        )

        # Encode using Mistral tokenizer
        tokens = self._mistral_tokenizer.encode_chat_completion(
            completion_request
        ).tokens

        print(f"[DEBUG] Encoded to {len(tokens)} tokens")
        return tokens

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

    def _parse_tool_calls(
        self, response_text: str
    ) -> tuple[Optional[List[dict]], str]:
        """Parse tool calls from model response (fallback format).

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
