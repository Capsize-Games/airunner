"""LangChain adapter for GGUF models via llama-cpp-python.

This adapter wraps llama-cpp-python for GGUF model inference,
providing the same interface as ChatHuggingFaceLocal for compatibility
with existing LangGraph workflows.

GGUF models are significantly smaller and faster than BitsAndBytes quantized
safetensors:
- Q4_K_M: ~4.1GB for 7B model (vs ~5.5GB for BnB 4-bit)
- Faster inference via optimized llama.cpp backend
- Native GPU acceleration via cuBLAS
"""

import os
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class PromptTemplate:
    """Prompt templates for different model architectures."""
    
    # ChatML format (Qwen, Qwen2, Qwen2.5, Qwen3, many fine-tunes)
    CHATML = {
        "system_start": "<|im_start|>system\n",
        "system_end": "<|im_end|>\n",
        "user_start": "<|im_start|>user\n",
        "user_end": "<|im_end|>\n",
        "assistant_start": "<|im_start|>assistant\n",
        "assistant_end": "<|im_end|>\n",
        "stop_tokens": ["<|im_end|>", "<|endoftext|>"],
    }
    
    # Llama 3/3.1/3.2/4 format
    LLAMA3 = {
        "system_start": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n",
        "system_end": "<|eot_id|>",
        "user_start": "<|start_header_id|>user<|end_header_id|>\n\n",
        "user_end": "<|eot_id|>",
        "assistant_start": "<|start_header_id|>assistant<|end_header_id|>\n\n",
        "assistant_end": "<|eot_id|>",
        "stop_tokens": ["<|eot_id|}}", "<|end_of_text|>"],
    }
    
    # Mistral/Ministral/Magistral format (v3 tokenizer)
    MISTRAL = {
        "system_start": "[INST] ",
        "system_end": "\n",
        "user_start": "",
        "user_end": " [/INST]",
        "assistant_start": "",
        "assistant_end": "</s>",
        "stop_tokens": ["</s>", "[INST]"],
    }
    
    # Mistral v7 (Nemo/newer) format with system support
    MISTRAL_V7 = {
        "system_start": "<s>[SYSTEM_PROMPT] ",
        "system_end": " [/SYSTEM_PROMPT]",
        "user_start": "[INST] ",
        "user_end": " [/INST]",
        "assistant_start": "",
        "assistant_end": "</s>",
        "stop_tokens": ["</s>", "[INST]"],
    }


def detect_model_template(model_path: str) -> dict:
    """Detect the appropriate prompt template based on model filename.
    
    Args:
        model_path: Path to the GGUF model file
        
    Returns:
        Prompt template dictionary
    """
    path_lower = model_path.lower()
    
    # Llama 3.x detection (Llama 4 models are too large for single-file GGUF)
    if any(x in path_lower for x in ["llama-3", "llama3", "meta-llama-3"]):
        return PromptTemplate.LLAMA3
    
    # Mistral/Ministral/Magistral detection
    if any(x in path_lower for x in ["mistral", "ministral", "magistral"]):
        # Newer Mistral models (Nemo, v7+) use different format
        if any(x in path_lower for x in ["nemo", "magistral"]):
            return PromptTemplate.MISTRAL_V7
        return PromptTemplate.MISTRAL
    
    # Qwen models (all versions use ChatML)
    if "qwen" in path_lower:
        return PromptTemplate.CHATML
    
    # Default to ChatML (most compatible)
    return PromptTemplate.CHATML


class ChatGGUF(BaseChatModel):
    """LangChain ChatModel adapter for GGUF models via llama-cpp-python.

    This adapter provides a unified interface for GGUF model inference,
    compatible with existing LangGraph workflows and tool calling.
    
    Supports multiple model architectures with automatic template detection:
    - Qwen/Qwen2/Qwen2.5/Qwen3 (ChatML format)
    - Llama 3/3.1/3.2/4 (Llama format)
    - Mistral/Ministral/Magistral (Mistral format)

    Attributes:
        model_path: Path to the GGUF model file
        n_ctx: Context window size (default: 8192 for modern models)
        n_gpu_layers: Number of layers to offload to GPU (-1 for all)
        n_batch: Batch size for prompt processing
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        repeat_penalty: Penalty for repeating tokens
        tools: Bound tools for function calling
        enable_thinking: Whether to enable thinking mode (Qwen3-style)
        prompt_template: Override auto-detected prompt template
    """

    model_path: str
    n_ctx: int = 4096  # Reduced from 8192 to save VRAM
    n_gpu_layers: int = -1  # -1 = all layers on GPU
    n_batch: int = 512
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 20
    repeat_penalty: float = 1.15
    flash_attn: bool = True  # Use flash attention to reduce VRAM
    tools: Optional[List[Any]] = None
    enable_thinking: bool = True
    prompt_template: Optional[Dict[str, Any]] = None  # Auto-detected if None
    _interrupted: bool = False
    _llama: Optional[Any] = None  # Llama instance from llama-cpp-python
    _template: Optional[Dict[str, Any]] = None  # Cached template

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

    @property
    def logger(self):
        """Get logger instance."""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(
                self.__class__.__name__,
                AIRUNNER_LOG_LEVEL
            )
        return self._logger

    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM type."""
        return "gguf-llama-cpp"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters for logging."""
        return {
            "model_path": self.model_path,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "flash_attn": self.flash_attn,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def model_post_init(self, __context: Any) -> None:
        """Initialize the llama-cpp-python model after Pydantic init."""
        super().model_post_init(__context)
        # Detect prompt template based on model filename
        if self.prompt_template is not None:
            self._template = self.prompt_template
        else:
            self._template = detect_model_template(self.model_path)
        self._load_model()

    def _load_model(self) -> None:
        """Load the GGUF model via llama-cpp-python."""
        if self._llama is not None:
            return

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python is required for GGUF support. "
                "Install with: pip install llama-cpp-python"
            )

        # Log detected template type
        template_name = "ChatML"
        if self._template == PromptTemplate.LLAMA3:
            template_name = "Llama3"
        elif self._template == PromptTemplate.MISTRAL:
            template_name = "Mistral"
        elif self._template == PromptTemplate.MISTRAL_V7:
            template_name = "Mistral-v7"
        
        self.logger.info(f"Loading GGUF model from {self.model_path}")
        self.logger.info(f"  Template: {template_name}, n_ctx={self.n_ctx}, n_gpu_layers={self.n_gpu_layers}")

        self._llama = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            n_batch=self.n_batch,
            flash_attn=self.flash_attn,
            type_k=8,  # KV cache key quantization: Q8_0 to save VRAM
            type_v=8,  # KV cache value quantization: Q8_0 to save VRAM
            verbose=False,  # Reduce log verbosity
        )

        self.logger.info("✓ GGUF model loaded successfully")

    def set_interrupted(self, value: bool) -> None:
        """Set the interrupted flag for stopping generation."""
        self._interrupted = value

    def should_stop_generation(self) -> bool:
        """Check if generation should stop."""
        return self._interrupted

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert LangChain messages to a prompt string.

        Uses auto-detected template based on model architecture:
        - ChatML for Qwen models
        - Llama format for Llama 3/3.1/3.2/4 models  
        - Mistral format for Mistral/Ministral/Magistral models
        
        CRITICAL: If tools are bound, injects tool instructions into the system
        message so the model knows what tools are available and how to use them.
        """
        t = self._template
        prompt_parts = []
        system_content = None

        # For Mistral format, we need to handle system differently
        # (it gets prepended to the first user message)
        is_mistral = t == PromptTemplate.MISTRAL
        
        for message in messages:
            if isinstance(message, SystemMessage):
                content = message.content
                # Inject tool instructions into system message if tools are bound
                if self.tools:
                    content = self._inject_tool_instructions(content)
                if is_mistral:
                    # Store system for prepending to first user message
                    system_content = content
                else:
                    prompt_parts.append(
                        f"{t['system_start']}{content}{t['system_end']}"
                    )
            elif isinstance(message, HumanMessage):
                content = message.content
                if is_mistral and system_content:
                    # Prepend system to first user message for Mistral
                    content = f"{system_content}\n\n{content}"
                    system_content = None
                prompt_parts.append(
                    f"{t['user_start']}{content}{t['user_end']}"
                )
            elif isinstance(message, AIMessage):
                prompt_parts.append(
                    f"{t['assistant_start']}{message.content}{t['assistant_end']}"
                )

        # Add assistant prefix for generation
        prompt_parts.append(t['assistant_start'])

        return "".join(prompt_parts)

    def _inject_tool_instructions(self, system_content: str) -> str:
        """Inject tool instructions into the system message.

        Args:
            system_content: The original system message content.

        Returns:
            System content with tool instructions appended.
        """
        tool_schemas_text = self.get_tool_schemas_text()
        if not tool_schemas_text:
            return system_content

        tool_instructions = f"""

## Available Tools

You have access to the following tools:

{tool_schemas_text}

## Tool Usage Instructions

When you need to use a tool, respond with a tool call in this EXACT format:
<tool_call>{{"name": "tool_name", "arguments": {{"arg1": "value1", "arg2": "value2"}}}}</tool_call>

CRITICAL RULES:
1. ALWAYS use the exact tool_call format shown above - do NOT invent your own format
2. NEVER hallucinate or make up tool results - you MUST call the tool and wait for real results
3. If you need information from the internet, USE the search_web tool - do NOT pretend to have results
4. After calling a tool, WAIT for the actual results before responding to the user
5. You can call multiple tools if needed, one at a time
6. Only respond with your final answer AFTER receiving real tool results"""

        return system_content + tool_instructions

    def _get_stop_tokens(self) -> List[str]:
        """Get stop tokens for the current model template."""
        return self._template.get("stop_tokens", ["<|im_end|>", "<|endoftext|>"])

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

        stop_sequences = stop or self._get_stop_tokens()

        response = self._llama(
            prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            repeat_penalty=self.repeat_penalty,
            stop=stop_sequences,
        )

        response_text = response["choices"][0]["text"]

        # Parse tool calls if tools are bound
        tool_calls = None
        if self.tools:
            tool_calls, response_text = self._parse_tool_calls(response_text)

        message = AIMessage(
            content=response_text,
            tool_calls=tool_calls or [],
        )

        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream response from messages.

        Args:
            messages: List of input messages
            stop: Optional stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional generation parameters

        Yields:
            ChatGenerationChunk objects with streamed content
        """
        prompt = self._messages_to_prompt(messages)
        stop_sequences = stop or self._get_stop_tokens()

        self._interrupted = False
        full_response = []

        for token in self._llama(
            prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            repeat_penalty=self.repeat_penalty,
            stop=stop_sequences,
            stream=True,
        ):
            if self._interrupted:
                break

            text = token["choices"][0]["text"]
            full_response.append(text)

            chunk = ChatGenerationChunk(
                message=AIMessageChunk(content=text)
            )

            if run_manager:
                run_manager.on_llm_new_token(text, chunk=chunk)

            yield chunk

        # Check for tool calls in final response
        if self.tools:
            response_text = "".join(full_response)
            tool_calls, _ = self._parse_tool_calls(response_text)

            if tool_calls:
                # Yield final chunk with tool calls
                yield ChatGenerationChunk(
                    message=AIMessageChunk(
                        content="",
                        tool_calls=tool_calls,
                    )
                )

    def _parse_tool_calls(
        self, response_text: str
    ) -> Tuple[Optional[List[Dict]], str]:
        """Parse tool calls from response text.

        Supports multiple formats:
        - JSON mode: {"name": "...", "arguments": {...}}
        - Qwen style: <tool_call>...</tool_call>

        Args:
            response_text: The raw response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        import json
        import re
        import uuid

        # Try Qwen-style tool call format
        tool_call_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        matches = re.findall(tool_call_pattern, response_text, re.DOTALL)

        if matches:
            tool_calls = []
            for match in matches:
                try:
                    call_data = json.loads(match)
                    tool_calls.append({
                        "id": str(uuid.uuid4()),
                        "name": call_data.get("name"),
                        "args": call_data.get("arguments", {}),
                    })
                except json.JSONDecodeError:
                    continue

            # Clean response text
            cleaned = re.sub(tool_call_pattern, "", response_text).strip()
            return tool_calls if tool_calls else None, cleaned

        # Try JSON mode format (single tool call)
        try:
            # Look for JSON object in response
            json_match = re.search(r'\{[^{}]*"name"[^{}]*\}', response_text)
            if json_match:
                call_data = json.loads(json_match.group())
                if "name" in call_data:
                    tool_calls = [{
                        "id": str(uuid.uuid4()),
                        "name": call_data["name"],
                        "args": call_data.get("arguments", call_data.get("args", {})),
                    }]
                    # Clean the JSON from the response text
                    cleaned = response_text.replace(json_match.group(), "").strip()
                    return tool_calls, cleaned
        except (json.JSONDecodeError, KeyError):
            pass

        return None, response_text

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, Callable, BaseTool]],
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind tools to this chat model.

        IMPORTANT: This method reuses the existing loaded model to avoid
        loading the GGUF file twice (which would double VRAM usage).

        Args:
            tools: List of tools to bind
            **kwargs: Additional arguments

        Returns:
            New instance with tools bound (shares the same llama model)
        """
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]

        # Simply update tools on this instance and return self
        # This avoids creating a new instance entirely, which is safe since
        # tools don't affect the underlying llama model state
        self.tools = formatted_tools
        return self

    def get_tool_schemas_text(self) -> str:
        """Get formatted tool schemas for injection into prompts."""
        if not self.tools:
            return ""

        tool_descriptions = []
        for tool in self.tools:
            func = tool.get("function", tool)
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            params = func.get("parameters", {}).get("properties", {})

            param_str = ", ".join(
                f"{k}: {v.get('type', 'any')}"
                for k, v in params.items()
            )

            tool_descriptions.append(f"- {name}({param_str}): {desc}")

        return "\n".join(tool_descriptions)


def find_gguf_file(model_dir: str) -> Optional[str]:
    """Find a GGUF file in a model directory.

    Args:
        model_dir: Directory to search

    Returns:
        Path to GGUF file if found, None otherwise
    """
    model_path = Path(model_dir)
    if not model_path.exists():
        return None

    # Look for GGUF files (prefer Q4_K_M)
    gguf_files = list(model_path.glob("*.gguf"))

    if not gguf_files:
        return None

    # Prefer Q4_K_M quantization
    for f in gguf_files:
        if "Q4_K_M" in f.name or "q4_k_m" in f.name:
            return str(f)

    # Fall back to first GGUF file
    return str(gguf_files[0])


def is_gguf_model(model_path: str) -> bool:
    """Check if a model path contains a GGUF model.

    Args:
        model_path: Path to model directory or file

    Returns:
        True if GGUF model found
    """
    path = Path(model_path)

    # Direct GGUF file
    if path.suffix == ".gguf":
        return path.exists()

    # Directory containing GGUF
    if path.is_dir():
        return find_gguf_file(str(path)) is not None

    return False
