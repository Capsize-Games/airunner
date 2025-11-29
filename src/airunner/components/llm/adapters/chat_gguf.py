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


class ChatGGUF(BaseChatModel):
    """LangChain ChatModel adapter for GGUF models via llama-cpp-python.

    This adapter provides a unified interface for GGUF model inference,
    compatible with existing LangGraph workflows and tool calling.

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
    _interrupted: bool = False
    _llama: Optional[Any] = None  # Llama instance from llama-cpp-python

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

        self.logger.info(f"Loading GGUF model from {self.model_path}")
        self.logger.info(f"  n_ctx={self.n_ctx}, n_gpu_layers={self.n_gpu_layers}, flash_attn={self.flash_attn}")

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

        Uses ChatML format which is widely supported by GGUF models.
        """
        prompt_parts = []

        for message in messages:
            if isinstance(message, SystemMessage):
                prompt_parts.append(f"<|im_start|>system\n{message.content}<|im_end|>")
            elif isinstance(message, HumanMessage):
                prompt_parts.append(f"<|im_start|>user\n{message.content}<|im_end|>")
            elif isinstance(message, AIMessage):
                prompt_parts.append(f"<|im_start|>assistant\n{message.content}<|im_end|>")

        # Add assistant prefix for generation
        prompt_parts.append("<|im_start|>assistant\n")

        return "\n".join(prompt_parts)

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

        stop_sequences = stop or ["<|im_end|>", "<|endoftext|>"]

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
        stop_sequences = stop or ["<|im_end|>", "<|endoftext|>"]

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
                    return tool_calls, response_text
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
