"""LangChain adapter for GGUF models via llama-cpp-python.

This adapter wraps llama-cpp-python for GGUF model inference with
model-specific tool-calling strategies.

GGUF models are significantly smaller and faster than BitsAndBytes quantized
safetensors:
- Q4_K_M: ~4.1GB for 7B model (vs ~5.5GB for BnB 4-bit)
- Faster inference via optimized llama.cpp backend
- Native GPU acceleration via cuBLAS

Qwen-family models can use llama.cpp native tool calling, while GPT-OSS runs
through a text-based tool path.
"""

import json
import re
import time
import uuid
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

from airunner_services.utils.application.log_hygiene import summarize_mapping_keys

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

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.llm.adapters.chat_gguf_tool_parsing import (
    build_gpt_oss_message_from_raw,
    extract_gpt_oss_recipient,
    extract_prefilled_gpt_oss_tool_json,
    forced_gpt_oss_tool_name,
    normalize_tool_payload,
    normalize_tool_value,
    parse_gpt_oss_commentary_tool_calls,
    parse_prefilled_gpt_oss_tool_call,
    parse_react_tool_calls,
)
from airunner_services.llm.adapters.chat_gguf_generation_helper import (
    generate_chat_result,
)
from airunner_services.llm.adapters.chat_gguf_model_helper import (
    _current_llama_cpp_version,
    _detect_chat_format,
    UnsupportedGGUFArchitectureError,
    apply_runtime_env_overrides,
    context_retry_sequence,
    detect_known_unsupported_architecture,
    estimate_gguf_kv_cache_gb,
    find_gguf_file,
    format_llama_tuning,
    is_gguf_model,
    llama_kwargs_for_context,
    load_llama_with_context_fallback,
    load_model,
    next_retry_context,
    read_gguf_architecture,
    resolve_llama_tuning,
    should_retry_context,
)
from airunner_services.llm.adapters.chat_gguf_prompt_helper import (
    apply_gpt_oss_reasoning_effort,
    apply_thinking_directive,
    build_gpt_oss_completion_kwargs,
    continue_prefilled_gpt_oss_tool_call,
    convert_langchain_tool_call,
    convert_langchain_tool_calls,
    convert_messages,
    format_gpt_oss_namespace,
    format_gpt_oss_object_type,
    format_gpt_oss_shared_definitions,
    format_gpt_oss_tool,
    format_gpt_oss_type,
    format_react_tool,
    gpt_oss_harmony_system_message,
    inject_gpt_oss_tool_instructions,
    inject_react_tool_instructions,
    inject_tool_instructions,
    prefilled_gpt_oss_tool_json_needs_continuation,
    render_gpt_oss_ai_message,
    render_gpt_oss_developer_message,
    render_gpt_oss_harmony_prompt,
    render_gpt_oss_prefilled_tool_call,
    render_gpt_oss_tool_message,
    render_harmony_message,
    stringify_harmony_content,
)
from airunner_services.llm.adapters.chat_gguf_streaming_helper import (
    finalize_native_tool_call_deltas,
    merge_native_tool_call_deltas,
    merge_streamed_text,
    stream_chat_result,
)
from airunner_services.llm.gpt_oss_parser import (
    CALL_TOKEN,
    CHANNEL_TOKEN,
    CONSTRAIN_TOKEN,
    END_TOKEN,
    GPTOSSStreamParser,
    MESSAGE_TOKEN,
    RETURN_TOKEN,
    START_TOKEN,
    has_gpt_oss_markup,
    looks_like_tool_argument_payload,
    parse_gpt_oss_response,
)
from airunner_services.llm.utils.stream_debug import print_stream_debug
from airunner_services.utils.application import get_logger
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
    gguf_runtime_profile: Optional[str] = None
    n_ctx: int = 32768  # Qwen3 native context (use YaRN for 131K)
    n_gpu_layers: int = -1
    n_batch: int = 256
    max_tokens: int = 32768  # Qwen3 recommended output length
    temperature: float = 0.6  # Qwen3 thinking mode recommended
    top_p: float = 0.95  # Qwen3 thinking mode recommended  
    top_k: int = 20  # Qwen3 recommended
    min_p: float = 0.0  # Qwen3 recommended (disabled)
    repeat_penalty: float = 1.15
    flash_attn: bool = True
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None  # "auto", "none", or specific tool name
    tool_calling_mode: str = "native"
    enable_thinking: bool = True
    reasoning_effort: str = "medium"
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
            "gguf_runtime_profile": self.gguf_runtime_profile,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "chat_format": self._detected_format,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def _runtime_signature(self, tuning: Dict[str, Any]) -> str:
        """Return one concise runtime signature for logs."""
        signature = {
            "profile": self.gguf_runtime_profile or "default",
            "chat_format": self._detected_format or "auto",
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "n_batch": tuning.get("n_batch", self.n_batch),
            "flash_attn": self.flash_attn,
            "offload_kqv": tuning.get("offload_kqv"),
            "op_offload": tuning.get("op_offload"),
        }
        return ", ".join(
            f"{key}={value}" for key, value in signature.items()
            if value is not None
        )

    def model_post_init(self, __context: Any) -> None:
        """Initialize the llama-cpp-python model after Pydantic init."""
        super().model_post_init(__context)
        if self.chat_format is not None:
            self._detected_format = self.chat_format
        else:
            self._detected_format = _detect_chat_format(self.model_path)
        self._load_model()

    def _uses_gpt_oss_parser(self) -> bool:
        """Return True when GPT-OSS Harmony content needs normalization."""
        model_path = str(self.model_path).lower()
        return self._detected_format == "gpt-oss" or "gpt-oss" in model_path

    def _use_raw_gpt_oss_completion(self) -> bool:
        """Return True when GPT-OSS should use raw Harmony prompting."""
        return (
            self._uses_gpt_oss_parser()
            and self.tool_calling_mode == "react"
            and bool(self.tools)
            and hasattr(self._llama, "create_completion")
        )

    def _normalized_reasoning_effort(self) -> str:
        """Return a valid GPT-OSS reasoning-effort value."""
        effort = str(self.reasoning_effort or "medium").strip().lower()
        if effort in {"low", "medium", "high"}:
            return effort
        return "medium"

    def _resolve_llama_tuning(self) -> Dict[str, Any]:
        """Resolve optional llama.cpp tuning overrides from the environment."""
        return resolve_llama_tuning(self)

    @staticmethod
    def _format_llama_tuning(tuning: Dict[str, Any]) -> str:
        """Format tuning fields for concise logging."""
        return format_llama_tuning(tuning)

    def _load_model(self) -> None:
        """Load the GGUF model via llama-cpp-python."""
        load_model(self)

    def _apply_runtime_env_overrides(self) -> None:
        """Apply optional llama.cpp runtime overrides from the environment."""
        apply_runtime_env_overrides(self)

    def _load_llama_with_context_fallback(
        self,
        llama_cls,
        base_kwargs: Dict[str, Any],
    ) -> None:
        """Load llama.cpp and retry smaller contexts on allocation failure."""
        load_llama_with_context_fallback(self, llama_cls, base_kwargs)

    def _llama_kwargs_for_context(
        self,
        base_kwargs: Dict[str, Any],
        n_ctx: int,
    ) -> Dict[str, Any]:
        """Return llama.cpp kwargs for one specific context size."""
        return llama_kwargs_for_context(self, base_kwargs, n_ctx)

    def _context_retry_sequence(self) -> tuple[int, ...]:
        """Return candidate context sizes for llama.cpp retry attempts."""
        return context_retry_sequence(self)

    @staticmethod
    def _next_retry_context(current_n_ctx: int) -> Optional[int]:
        """Return the next smaller context retry target when one exists."""
        return next_retry_context(current_n_ctx)

    @staticmethod
    def _should_retry_context(exc: Exception, n_ctx: int) -> bool:
        """Return True when one smaller llama context should be attempted."""
        return should_retry_context(exc, n_ctx)

    def _reload_with_tools(self) -> None:
        """No-op: tool bindings do not require runtime reloading."""
        pass

    def clear_bound_tools(self) -> None:
        """Clear previously bound tools from the live model instance."""
        self.tools = None
        self.tool_choice = None

    def _use_native_tool_calling(self) -> bool:
        """Return True when llama.cpp native tools should be used."""
        return (
            bool(self.tools)
            and self.tool_choice != "none"
            and self.tool_calling_mode != "react"
        )

    def set_interrupted(self, value: bool) -> None:
        """Set the interrupted flag for stopping generation."""
        self._interrupted = value

    def should_stop_generation(self) -> bool:
        """Check if generation should stop."""
        return self._interrupted

    def _convert_messages(
        self,
        messages: List[BaseMessage],
    ) -> List[Dict[str, Any]]:
        """Convert LangChain messages to llama-cpp-python format."""
        return convert_messages(self, messages)

    def _apply_gpt_oss_reasoning_effort(
        self,
        converted: List[Dict[str, Any]],
    ) -> None:
        """Inject the documented GPT-OSS reasoning-effort directive."""
        apply_gpt_oss_reasoning_effort(self, converted)

    def _inject_tool_instructions(self, system_content: str) -> str:
        """Inject tool instructions into the system prompt."""
        return inject_tool_instructions(self, system_content)

    def _inject_gpt_oss_tool_instructions(
        self,
        system_content: str,
    ) -> str:
        """Inject Harmony-style tool instructions for GPT-OSS."""
        return inject_gpt_oss_tool_instructions(self, system_content)

    def _gpt_oss_harmony_system_message(self) -> str:
        """Return the top-level Harmony system message."""
        return gpt_oss_harmony_system_message(self)

    def _render_harmony_message(
        self,
        role: str,
        content: str,
        *,
        channel: Optional[str] = None,
        recipient: Optional[str] = None,
        content_type: Optional[str] = None,
        terminator: str = END_TOKEN,
    ) -> str:
        """Render one Harmony protocol message."""
        return render_harmony_message(
            role,
            content,
            channel=channel,
            recipient=recipient,
            content_type=content_type,
            terminator=terminator,
        )

    def _stringify_harmony_content(self, content: Any) -> str:
        """Convert one LangChain content payload into Harmony text."""
        return stringify_harmony_content(content)

    def _render_gpt_oss_developer_message(
        self,
        messages: List[BaseMessage],
    ) -> str:
        """Render the developer instruction layer for raw Harmony prompts."""
        return render_gpt_oss_developer_message(self, messages)

    def _render_gpt_oss_ai_message(
        self,
        message: AIMessage,
    ) -> List[str]:
        """Render one historical AI message into Harmony messages."""
        return render_gpt_oss_ai_message(self, message)

    def _render_gpt_oss_tool_message(self, message: ToolMessage) -> str:
        """Render one tool-result message into Harmony format."""
        return render_gpt_oss_tool_message(message)

    def _forced_gpt_oss_tool_name(self) -> Optional[str]:
        return forced_gpt_oss_tool_name(self)

    def _render_gpt_oss_prefilled_tool_call(self, tool_name: str) -> str:
        """Render a partial Harmony tool call for one forced tool."""
        return render_gpt_oss_prefilled_tool_call(tool_name)

    def _render_gpt_oss_harmony_prompt(
        self,
        messages: List[BaseMessage],
    ) -> str:
        """Render LangChain messages as one raw Harmony prompt."""
        return render_gpt_oss_harmony_prompt(self, messages)

    def _build_gpt_oss_completion_kwargs(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]],
        *,
        stream: bool,
    ) -> Dict[str, Any]:
        """Build llama.cpp completion kwargs for raw Harmony prompting."""
        return build_gpt_oss_completion_kwargs(
            self,
            messages,
            stop,
            stream=stream,
        )

    def _prefilled_gpt_oss_tool_json_needs_continuation(
        self,
        raw_text: str,
    ) -> bool:
        """Return True when a forced prefilled tool body looks truncated."""
        return prefilled_gpt_oss_tool_json_needs_continuation(
            self,
            raw_text,
        )

    def _continue_prefilled_gpt_oss_tool_call(
        self,
        completion_kwargs: Dict[str, Any],
        raw_text: str,
    ) -> str:
        """Continue a truncated prefilled Harmony tool call body."""
        return continue_prefilled_gpt_oss_tool_call(
            self,
            completion_kwargs,
            raw_text,
        )

    def _build_gpt_oss_message_from_raw(
        self,
        raw_text: str,
    ) -> AIMessage:
        return build_gpt_oss_message_from_raw(self, raw_text)

    def _format_gpt_oss_namespace(self) -> str:
        """Format bound tools as a Harmony functions namespace."""
        return format_gpt_oss_namespace(self)

    def _format_gpt_oss_shared_definitions(
        self,
        shared_defs: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Format shared schema definitions for Harmony tool prompts."""
        return format_gpt_oss_shared_definitions(shared_defs)

    def _format_gpt_oss_tool(self, tool: Dict[str, Any]) -> List[str]:
        """Format one tool schema as a Harmony type definition."""
        return format_gpt_oss_tool(tool)

    def _format_gpt_oss_type(
        self,
        schema: Dict[str, Any],
        indent_level: int = 0,
    ) -> str:
        """Convert a JSON schema fragment to a Harmony-style type."""
        return format_gpt_oss_type(schema, indent_level)

    def _format_gpt_oss_object_type(
        self,
        schema: Dict[str, Any],
        indent_level: int,
    ) -> str:
        """Format one JSON object schema as an inline type block."""
        return format_gpt_oss_object_type(schema, indent_level)

    def _inject_react_tool_instructions(self, system_content: str) -> str:
        """Inject ReAct-style tool instructions for text tool calling."""
        return inject_react_tool_instructions(self, system_content)

    def _format_react_tool(self, tool: Dict[str, Any]) -> str:
        """Format one OpenAI tool schema as a compact ReAct tool line."""
        return format_react_tool(tool)

    def _convert_langchain_tool_calls(
        self,
        tool_calls: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Convert LangChain tool call records to OpenAI chat format."""
        return convert_langchain_tool_calls(tool_calls)

    def _convert_langchain_tool_call(
        self,
        tool_call: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Convert one LangChain tool call to OpenAI chat format."""
        return convert_langchain_tool_call(tool_call)

    def _apply_thinking_directive(
        self,
        converted: List[Dict[str, Any]],
    ) -> None:
        """Prefix the final Qwen3 user turn with a no-think directive."""
        apply_thinking_directive(self, converted)

    def _extract_tool_calls(
        self, content: str
    ) -> tuple[List[Dict[str, Any]], str]:
        """Extract text-encoded tool calls and cleaned response text."""
        if self.tool_calling_mode == "json":
            json_calls, json_text = self._parse_json_tool_calls(content)
            if json_calls:
                return json_calls, json_text

        react_calls, react_text = self._parse_react_tool_calls(content)
        if react_calls:
            return react_calls, react_text

        xml_calls, xml_text = self._parse_xml_tool_calls(content)
        return xml_calls, xml_text

    def _parse_json_tool_calls(
        self, content: str
    ) -> tuple[List[Dict[str, Any]], str]:
        """Parse JSON-mode tool calls embedded in assistant text."""
        tool_calls: List[Dict[str, Any]] = []
        cleaned = content
        pattern = r'\{(?:[^{}]|(\{(?:[^{}]|\{[^{}]*\})*\}))*\}'

        for match in re.finditer(pattern, content or "", re.DOTALL):
            json_str = match.group(0)
            try:
                payload = self._normalize_tool_payload(json.loads(json_str))
            except json.JSONDecodeError:
                continue
            if not self._is_json_tool_payload(payload):
                continue
            tool_calls.append(self._build_json_tool_call(payload))
            cleaned = cleaned.replace(json_str, "").strip()

        return tool_calls, cleaned

    def _is_json_tool_payload(self, payload: Any) -> bool:
        """Return whether one parsed JSON object is a tool call payload."""
        return isinstance(payload, dict) and bool(
            payload.get("tool") or payload.get("name")
        )

    def _build_json_tool_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Build one normalized tool call from JSON-mode output."""
        return {
            "id": str(uuid.uuid4()),
            "name": payload.get("tool") or payload.get("name"),
            "args": payload.get("arguments") or payload.get("args") or {},
            "type": "tool_call",
        }

    def _normalize_tool_payload(self, payload: Any) -> Any:
        return normalize_tool_payload(payload)

    def _normalize_tool_value(self, key: str, value: Any) -> Any:
        return normalize_tool_value(key, value)

    def _parse_gpt_oss_commentary_tool_calls(
        self, content: str
    ) -> List[Dict[str, Any]]:
        return parse_gpt_oss_commentary_tool_calls(self, content)

    def _extract_prefilled_gpt_oss_tool_json(self, content: str) -> str:
        return extract_prefilled_gpt_oss_tool_json(content)

    def _parse_prefilled_gpt_oss_tool_call(
        self,
        content: str,
    ) -> List[Dict[str, Any]]:
        return parse_prefilled_gpt_oss_tool_call(self, content)

    def _extract_gpt_oss_recipient(
        self,
        role_header: Optional[str],
        channel_header: str,
    ) -> Optional[str]:
        return extract_gpt_oss_recipient(role_header, channel_header)

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse text-encoded tool calls from model response text."""
        tool_calls, _ = self._extract_tool_calls(content)
        return tool_calls

    def _parse_xml_tool_calls(
        self, content: str
    ) -> tuple[List[Dict[str, Any]], str]:
        """Parse XML-tagged tool calls from model response text."""
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

        cleaned = re.sub(
            r'<tool_call>\s*.*?\s*</tool_call>',
            '',
            content,
            flags=re.DOTALL,
        ).strip()
        return tool_calls, cleaned

    def _parse_react_tool_calls(
        self, content: str
    ) -> tuple[List[Dict[str, Any]], str]:
        return parse_react_tool_calls(self, content)

    def _parse_native_tool_calls(
        self, raw_tool_calls: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Parse OpenAI-style native tool calls from llama.cpp responses."""
        tool_calls: List[Dict[str, Any]] = []

        for raw_call in raw_tool_calls or []:
            function = raw_call.get("function", {}) if isinstance(raw_call, dict) else {}
            arguments = function.get("arguments", {})

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments.strip() else {}
                except json.JSONDecodeError:
                    self.logger.warning(
                        "Failed to parse native tool arguments for %s",
                        function.get("name", "unknown"),
                    )
                    arguments = {}

            tool_calls.append(
                {
                    "id": raw_call.get("id") or str(uuid.uuid4()),
                    "name": function.get("name"),
                    "args": arguments if isinstance(arguments, dict) else {},
                    "type": "tool_call",
                }
            )

        return tool_calls

    @staticmethod
    def _merge_streamed_text(existing: str, fragment: str) -> str:
        return merge_streamed_text(existing, fragment)

    def _merge_native_tool_call_deltas(
        self,
        tool_call_buffers: Dict[int, Dict[str, Any]],
        raw_tool_calls: Optional[List[Dict[str, Any]]],
    ) -> None:
        merge_native_tool_call_deltas(self, tool_call_buffers, raw_tool_calls)

    def _finalize_native_tool_call_deltas(
        self, tool_call_buffers: Dict[int, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return finalize_native_tool_call_deltas(self, tool_call_buffers)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        return generate_chat_result(
            self,
            messages,
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        return stream_chat_result(
            self,
            messages,
            stop=stop,
            run_manager=run_manager,
            **kwargs,
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
            Copy of this model with tools bound
        """
        bound_model = self.model_copy(deep=False)

        # Convert tools to OpenAI format
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]

        bound_model.tools = formatted_tools
        bound_model.tool_choice = tool_choice

        # Reload model with function calling format if needed
        bound_model._reload_with_tools()

        return bound_model

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
