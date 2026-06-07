"""Execution and binding mixin for the GGUF chat adapter."""

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
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from airunner_services.llm.adapters.chat_gguf_generation_helper import (
    generate_chat_result,
)
from airunner_services.llm.adapters.chat_gguf_streaming_common import (
    finalize_native_tool_call_deltas,
    merge_native_tool_call_deltas,
    merge_streamed_text,
)
from airunner_services.llm.adapters.chat_gguf_streaming_helper import (
    stream_chat_result,
)


class ChatGGUFExecutionMixin:
    """Provide generation, streaming, and tool-binding wrappers."""

    @staticmethod
    def _merge_streamed_text(existing: str, fragment: str) -> str:
        """Merge one streamed text fragment into the accumulated text."""
        return merge_streamed_text(existing, fragment)

    def _merge_native_tool_call_deltas(
        self,
        tool_call_buffers: Dict[int, Dict[str, Any]],
        raw_tool_calls: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Merge native-tool delta chunks into buffered tool calls."""
        merge_native_tool_call_deltas(self, tool_call_buffers, raw_tool_calls)

    def _finalize_native_tool_call_deltas(
        self,
        tool_call_buffers: Dict[int, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Finalize buffered native-tool delta chunks into tool calls."""
        return finalize_native_tool_call_deltas(self, tool_call_buffers)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate one non-streaming chat result."""
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
        """Generate streaming chat chunks."""
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
        """Bind tools to this chat model."""
        bound_model = self.model_copy(deep=False)
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        bound_model.tools = formatted_tools
        bound_model.tool_choice = tool_choice
        bound_model._reload_with_tools()
        return bound_model

    def get_tool_schemas_text(self) -> str:
        """Get formatted tool schemas for compatibility and debugging."""
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
            for key, value in params.items():
                req = "*" if key in required else ""
                param_strs.append(f"{key}{req}: {value.get('type', 'any')}")
            lines.append(f"- {name}({', '.join(param_strs)}): {desc}")
        return "\n".join(lines)
