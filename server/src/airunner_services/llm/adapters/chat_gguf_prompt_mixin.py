"""Prompt-rendering mixin for the GGUF chat adapter."""

from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from airunner_services.llm.adapters.chat_gguf_prompt_harmony_completion import (
    build_gpt_oss_completion_kwargs,
    continue_prefilled_gpt_oss_tool_call,
    prefilled_gpt_oss_tool_json_needs_continuation,
    render_gpt_oss_harmony_prompt,
)
from airunner_services.llm.adapters.chat_gguf_prompt_harmony_render import (
    render_gpt_oss_ai_message,
    render_gpt_oss_developer_message,
    render_gpt_oss_prefilled_tool_call,
    render_gpt_oss_tool_message,
    render_harmony_message,
    stringify_harmony_content,
)
from airunner_services.llm.adapters.chat_gguf_prompt_instructions import (
    apply_gpt_oss_reasoning_effort,
    apply_thinking_directive,
    format_react_tool,
    gpt_oss_harmony_system_message,
    inject_gpt_oss_tool_instructions,
    inject_react_tool_instructions,
    inject_tool_instructions,
)
from airunner_services.llm.adapters.chat_gguf_prompt_messages import (
    convert_messages,
)
from airunner_services.llm.adapters.chat_gguf_prompt_schema import (
    format_gpt_oss_namespace,
    format_gpt_oss_object_type,
    format_gpt_oss_shared_definitions,
    format_gpt_oss_tool,
    format_gpt_oss_type,
)
from airunner_services.llm.adapters.chat_gguf_tool_call_conversion import (
    convert_langchain_tool_call,
    convert_langchain_tool_calls,
)
from airunner_services.llm.adapters.chat_gguf_tool_parsing_gpt_oss import (
    build_gpt_oss_message_from_raw,
    forced_gpt_oss_tool_name,
)
from airunner_services.llm.gpt_oss_parser import END_TOKEN


class ChatGGUFPromptMixin:
    """Provide prompt and message wrappers for ChatGGUF."""

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
        """Return the forced GPT-OSS tool name when one is configured."""
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
        return prefilled_gpt_oss_tool_json_needs_continuation(self, raw_text)

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
        """Normalize one raw GPT-OSS response into an AI message."""
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
