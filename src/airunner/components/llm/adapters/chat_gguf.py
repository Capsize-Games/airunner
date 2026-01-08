"""LangChain adapter for GGUF models via llama-cpp-python.

This adapter wraps llama-cpp-python for GGUF model inference,
using Qwen3's native tool calling format with <tool_call> XML tags.

GGUF models are significantly smaller and faster than BitsAndBytes quantized
safetensors:
- Q4_K_M: ~4.1GB for 7B model (vs ~5.5GB for BnB 4-bit)
- Faster inference via optimized llama.cpp backend
- Native GPU acceleration via cuBLAS

For Qwen3 models, this injects tool definitions in the system prompt and
parses <tool_call> tags from responses (matching Qwen3's native format).
"""

import json
import re
import uuid
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
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
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class UnsupportedGGUFArchitectureError(Exception):
    """Raised when a GGUF model uses an architecture not supported by llama-cpp-python.
    
    This allows the factory to catch this specific error and fall back to
    transformers-based loading.
    """
    
    def __init__(self, architecture: str, model_path: str):
        self.architecture = architecture
        self.model_path = model_path
        super().__init__(
            f"GGUF model architecture '{architecture}' is not supported by llama-cpp-python. "
            f"Model: {model_path}. Consider using safetensors with transformers instead."
        )


def _detect_chat_format(model_path: str) -> str:
    """Detect the appropriate chat format based on model filename.
    
    Args:
        model_path: Path to the GGUF model file
        
    Returns:
        Chat format string for llama-cpp-python
    """
    path_lower = model_path.lower()
    
    # Qwen models use chatml
    if "qwen" in path_lower:
        return "chatml"
    
    # Llama 3.x 
    if any(x in path_lower for x in ["llama-3", "llama3", "meta-llama-3"]):
        return "llama-3"
    
    # Mistral
    if any(x in path_lower for x in ["mistral", "ministral", "magistral"]):
        return "mistral-instruct"
    
    # Default to chatml (most compatible)
    return "chatml"


class ChatGGUF(BaseChatModel):
    """LangChain ChatModel adapter for GGUF models via llama-cpp-python.

    This adapter uses llama-cpp-python's NATIVE function calling support
    via create_chat_completion() with tools parameter. This is the proper
    way to do tool calling with Qwen3 and other modern models.
    
    Key features:
    - Uses native chat completion API (not manual prompt building)
    - Proper Hermes-style function calling (not ReAct)
    - Automatic chat format detection from model name
    - Full streaming support
    - Thinking mode support for Qwen3

    Attributes:
        model_path: Path to the GGUF model file
        n_ctx: Context window size (32768 native for Qwen3, up to 131072 with YaRN)
        n_gpu_layers: Number of layers to offload to GPU (-1 for all)
        max_tokens: Maximum tokens to generate (32768 for Qwen3)
        temperature: Sampling temperature
        tools: Bound tools for function calling (OpenAI format)
        enable_thinking: Whether to enable thinking mode (Qwen3-style)
        chat_format: Override auto-detected chat format
        use_yarn: Enable YaRN for extended context (requires more VRAM)
    """

    model_path: str
    n_ctx: int = 32768  # Qwen3 native context (use YaRN for 131K)
    n_gpu_layers: int = -1
    n_batch: int = 512
    max_tokens: int = 32768  # Qwen3 recommended output length
    temperature: float = 0.6  # Qwen3 thinking mode recommended
    top_p: float = 0.95  # Qwen3 thinking mode recommended  
    top_k: int = 20  # Qwen3 recommended
    min_p: float = 0.0  # Qwen3 recommended (disabled)
    repeat_penalty: float = 1.15
    flash_attn: bool = True
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None  # "auto", "none", or specific tool name
    enable_thinking: bool = True
    chat_format: Optional[str] = None  # Auto-detected if None
    use_yarn: bool = False  # Disabled by default - requires more VRAM
    yarn_orig_ctx: int = 32768  # Qwen3 native context length
    _interrupted: bool = False
    _llama: Optional[Any] = None
    _detected_format: Optional[str] = None

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
            "chat_format": self._detected_format,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    @property 
    def tool_calling_mode(self) -> str:
        """Return tool calling mode for compatibility with workflow manager."""
        # We use native function calling, not ReAct
        return "native"

    def model_post_init(self, __context: Any) -> None:
        """Initialize the llama-cpp-python model after Pydantic init."""
        super().model_post_init(__context)
        self._detected_format = self.chat_format or _detect_chat_format(self.model_path)
        self._load_model()

    def _load_model(self) -> None:
        """Load the GGUF model via llama-cpp-python.
        
        Raises:
            ImportError: If llama-cpp-python is not installed
            UnsupportedGGUFArchitectureError: If the model architecture is not supported
            RuntimeError: For other loading errors
        """
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
        self.logger.info(
            f"  chat_format={self._detected_format}, n_ctx={self.n_ctx}, "
            f"n_gpu_layers={self.n_gpu_layers}"
        )

        # Use standard chatml format - we handle tool calling via prompt injection
        # and <tool_call> tag parsing (Qwen3 native format)
        
        # Build kwargs with optional YaRN support for extended context
        llama_kwargs = {
            "model_path": self.model_path,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "n_batch": self.n_batch,
            "flash_attn": self.flash_attn,
            "chat_format": self._detected_format,
            "type_k": 8,  # KV cache quantization to save VRAM
            "type_v": 8,
            "verbose": False,
        }
        
        # Add YaRN parameters for extended context (131K)
        # YaRN (Yet another RoPE extensioN) allows extending context beyond native limit
        if self.use_yarn and self.n_ctx > self.yarn_orig_ctx:
            self.logger.info(
                f"Enabling YaRN for extended context: {self.yarn_orig_ctx} -> {self.n_ctx}"
            )
            # rope_scaling_type: 2 = YARN in llama.cpp
            llama_kwargs["rope_scaling_type"] = 2
            llama_kwargs["yarn_orig_ctx"] = self.yarn_orig_ctx
            # Calculate scaling factor: target_ctx / original_ctx
            factor = self.n_ctx / self.yarn_orig_ctx
            llama_kwargs["yarn_ext_factor"] = factor
            llama_kwargs["yarn_attn_factor"] = 1.0
            llama_kwargs["yarn_beta_fast"] = 32.0
            llama_kwargs["yarn_beta_slow"] = 1.0
        
        try:
            self._llama = Llama(**llama_kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            # Check for unsupported architecture error from llama.cpp
            if "unknown model architecture" in error_msg:
                # Extract architecture name from error message if possible
                # Error format: "unknown model architecture: 'mistral3'"
                import re
                arch_match = re.search(r"unknown model architecture[:\s]*['\"]?(\w+)['\"]?", error_msg)
                architecture = arch_match.group(1) if arch_match else "unknown"
                raise UnsupportedGGUFArchitectureError(architecture, self.model_path)
            elif "failed to load model" in error_msg:
                # Generic llama.cpp load failure - could also be architecture issue
                raise RuntimeError(
                    f"Failed to load GGUF model from {self.model_path}: {e}. "
                    "This may be due to an unsupported model architecture or corrupted file."
                )
            else:
                raise

        self.logger.info("✓ GGUF model loaded successfully")

    def _reload_with_tools(self) -> None:
        """No-op: We don't need to reload for Qwen3's native tool format."""
        # Qwen3 uses <tool_call> tags which we parse from output
        # No special chat format needed
        pass

    def set_interrupted(self, value: bool) -> None:
        """Set the interrupted flag for stopping generation."""
        self._interrupted = value

    def should_stop_generation(self) -> bool:
        """Check if generation should stop."""
        return self._interrupted

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Convert LangChain messages to llama-cpp-python format.
        
        Args:
            messages: LangChain message objects
            
        Returns:
            List of message dicts for create_chat_completion
        """
        converted = []
        tool_instructions_added = False
        
        for msg in messages:
            if isinstance(msg, SystemMessage):
                content = msg.content
                # Inject Qwen3-style tool instructions into system message
                if self.tools and not tool_instructions_added:
                    content = self._inject_tool_instructions(content)
                    tool_instructions_added = True
                converted.append({
                    "role": "system",
                    "content": content,
                })
            elif isinstance(msg, HumanMessage):
                converted.append({
                    "role": "user",
                    "content": msg.content,
                })
            elif isinstance(msg, AIMessage):
                msg_dict = {
                    "role": "assistant",
                    "content": msg.content or "",
                }
                converted.append(msg_dict)
            elif isinstance(msg, ToolMessage):
                # Format tool results as user messages with context
                converted.append({
                    "role": "user",
                    "content": f"Tool result for {getattr(msg, 'name', 'tool')}:\n{msg.content}",
                })
        
        # If no system message but we have tools, add one
        if self.tools and not tool_instructions_added:
            tool_system = self._inject_tool_instructions("")
            converted.insert(0, {"role": "system", "content": tool_system})
        
        return converted

    def _inject_tool_instructions(self, system_content: str) -> str:
        """Inject Qwen3-style tool calling instructions into system prompt.
        
        Args:
            system_content: Existing system prompt content
            
        Returns:
            System content with tool instructions appended
        """
        if not self.tools:
            return system_content
        
        # Respect tool_choice="none" - don't inject tool instructions
        if self.tool_choice == "none":
            return system_content
            
        # Build Qwen3-style tool definitions
        tool_defs = []
        for tool in self.tools:
            tool_defs.append(json.dumps(tool))
        
        tools_json = "\n".join(tool_defs)
        
        tool_instructions = f"""

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tools_json}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": "<function-name>", "arguments": <args-json-object>}}
</tool_call>"""

        return system_content + tool_instructions

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse <tool_call> tags from model response.
        
        Args:
            content: Model response text
            
        Returns:
            List of tool call dicts with id, name, and args
        """
        tool_calls = []
        
        # Find all <tool_call>...</tool_call> blocks
        pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                # Parse the JSON inside the tool_call tags
                call_data = json.loads(match.strip())
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "name": call_data.get("name"),
                    "args": call_data.get("arguments", {}),
                    "type": "tool_call",
                })
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse tool call JSON: {e}")
                continue
                
        return tool_calls

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response using native chat completion API.

        For Qwen3 models, tools are injected into the system prompt and
        tool calls are parsed from <tool_call> XML tags in the response.

        Args:
            messages: List of input messages
            stop: Optional stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional generation parameters

        Returns:
            ChatResult with generated response
        """
        converted_messages = self._convert_messages(messages)
        
        # Build kwargs for create_chat_completion
        # NOTE: We do NOT pass tools here - they are in the system prompt
        # and the model will use <tool_call> tags which we parse ourselves
        chat_kwargs = {
            "messages": converted_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "min_p": self.min_p,
            "repeat_penalty": self.repeat_penalty,
            "stream": False,
        }
        
        if stop:
            chat_kwargs["stop"] = stop

        if self.tools:
            self.logger.debug(f"[TOOL CALL] {len(self.tools)} tools injected in system prompt")
        else:
            self.logger.debug("[TOOL CALL] No tools bound")

        # Call native chat completion
        self.logger.debug(f"[TOOL CALL] Calling create_chat_completion with chat_format={self._detected_format}")
        response = self._llama.create_chat_completion(**chat_kwargs)
        self.logger.debug(f"[TOOL CALL] Response: {response}")
        
        # Extract response
        choice = response["choices"][0]
        message_data = choice.get("message", {})
        content = message_data.get("content", "") or ""
        
        # Handle thinking content (Qwen3)
        thinking_content = None
        if self.enable_thinking and hasattr(message_data, "get"):
            thinking_content = message_data.get("reasoning_content")
        
        # Parse tool calls from <tool_call> tags in content (Qwen3 format)
        tool_calls = self._parse_tool_calls(content)
        
        if tool_calls:
            self.logger.debug(f"[TOOL CALL] Parsed {len(tool_calls)} tool calls from response")
            # Remove <tool_call> tags from content for cleaner display
            content = re.sub(r'<tool_call>\s*.*?\s*</tool_call>', '', content, flags=re.DOTALL).strip()

        # Build AIMessage
        additional_kwargs = {}
        if thinking_content:
            additional_kwargs["thinking_content"] = thinking_content
            
        message = AIMessage(
            content=content,
            tool_calls=tool_calls,
            additional_kwargs=additional_kwargs,
        )

        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream response using native chat completion API.

        For Qwen3 models, tools are in the system prompt and tool calls
        are parsed from <tool_call> XML tags at the end of streaming.

        Args:
            messages: List of input messages
            stop: Optional stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional generation parameters

        Yields:
            ChatGenerationChunk objects with streamed content
        """
        self.logger.info("[ChatGGUF._stream] Starting stream generation")
        converted_messages = self._convert_messages(messages)
        self.logger.info(f"[ChatGGUF._stream] Converted {len(converted_messages)} messages")
        
        # NOTE: We do NOT pass tools - they are in the system prompt
        chat_kwargs = {
            "messages": converted_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "min_p": self.min_p,
            "repeat_penalty": self.repeat_penalty,
            "stream": True,
        }
        
        if stop:
            chat_kwargs["stop"] = stop

        self._interrupted = False
        full_content = []
        
        self.logger.info(f"[ChatGGUF._stream] Calling create_chat_completion with max_tokens={self.max_tokens}")
        self.logger.info(f"[ChatGGUF._stream] Number of tools bound: {len(self.tools) if self.tools else 0}")
        self.logger.info(f"[ChatGGUF._stream] tool_choice: {self.tool_choice}")
        
        chunk_count = 0
        for chunk in self._llama.create_chat_completion(**chat_kwargs):
            chunk_count += 1
            if chunk_count == 1:
                self.logger.info(f"[ChatGGUF._stream] First chunk received")
            if self._interrupted:
                break

            delta = chunk.get("choices", [{}])[0].get("delta", {})
            
            # Handle content
            if "content" in delta and delta["content"]:
                text = delta["content"]
                full_content.append(text)
                
                chunk_msg = ChatGenerationChunk(
                    message=AIMessageChunk(content=text)
                )
                
                if run_manager:
                    run_manager.on_llm_new_token(text, chunk=chunk_msg)
                    
                yield chunk_msg

        # After streaming completes, parse <tool_call> tags from full content
        self.logger.info(f"[ChatGGUF._stream] Stream loop finished. Total chunks: {chunk_count}, content length: {len(''.join(full_content))}")
        full_text = "".join(full_content)
        tool_calls = self._parse_tool_calls(full_text)
        
        if tool_calls:
            self.logger.debug(f"[TOOL CALL] Parsed {len(tool_calls)} tool calls from streamed response")
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    tool_calls=tool_calls,
                )
            )

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, Callable, BaseTool]],
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind tools to this chat model.

        Args:
            tools: List of tools to bind (will be converted to OpenAI format)
            tool_choice: Tool selection strategy ("auto", "none", or tool name)
            **kwargs: Additional arguments

        Returns:
            Self with tools bound
        """
        # Convert tools to OpenAI format
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        
        self.tools = formatted_tools
        self.tool_choice = tool_choice
        
        # Reload model with function calling format if needed
        self._reload_with_tools()
        
        return self

    def get_tool_schemas_text(self) -> str:
        """Get formatted tool schemas for compatibility.
        
        Note: This is mainly for debugging/logging. The actual tool
        formatting is handled by llama-cpp-python's chat format.
        """
        if not self.tools:
            return ""

        lines = []
        for tool in self.tools:
            func = tool.get("function", tool)
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            params = func.get("parameters", {}).get("properties", {})
            required = func.get("parameters", {}).get("required", [])

            param_strs = []
            for k, v in params.items():
                req = "*" if k in required else ""
                param_strs.append(f"{k}{req}: {v.get('type', 'any')}")

            lines.append(f"- {name}({', '.join(param_strs)}): {desc}")

        return "\n".join(lines)


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
