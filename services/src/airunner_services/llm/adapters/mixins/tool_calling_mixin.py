"""Tool calling operations for HuggingFace chat models."""

from typing import List, Optional, Dict, Tuple

from airunner_services.llm.adapters.chat_gguf_tool_parsing_react import (
    parse_react_tool_calls,
)
from airunner_services.llm.adapters.mixins.tool_call_json_parsing import (
    try_parse_embedded_json,
    try_parse_json_blocks,
)
from airunner_services.llm.adapters.mixins.tool_prompt_formatting import (
    build_tool_descriptions,
    format_parameters,
    format_tools_for_prompt,
)
from airunner_services.llm.adapters.mixins.tool_prompt_instructions import (
    build_tool_instructions,
)
from airunner_services.llm.adapters.mixins.tool_call_response_parsing import (
    parse_json_mode_tool_calls,
    parse_mistral_tool_calls,
)


class ToolCallingMixin:
    """Handles tool calling parsing and formatting for chat models.

    This mixin provides functionality for:
    - Formatting tools for prompts
    - Parsing tool calls from responses (Mistral native, JSON mode, ReAct)
    - Converting between tool formats
    """

    def get_tool_schemas_text(self) -> str:
        """Get tool schemas as formatted text for system prompt.

        This should be called by the workflow manager to add tool descriptions
        to the system prompt, rather than injecting into message history.

        For Mistral native mode and JSON mode (with bind_tools), tools are encoded
        in the tokenization or handled by LangChain's bind_tools(), so we return
        empty string to avoid duplicate/conflicting tool descriptions.

        For ReAct mode, we need to add manual tool instructions.

        Returns:
            Formatted tool descriptions or empty string if using native/json modes
        """
        # Skip tool instructions if using native modes (Mistral or JSON with bind_tools)
        # In these modes, the chat template or bind_tools() handles tool formatting
        if self.use_mistral_native or (
            self.tool_calling_mode == "json" and self.use_json_mode
        ):
            return ""

        # For ReAct mode, we need manual tool instructions
        return self._format_tools_for_prompt() if self.tools else ""

    def _format_tools_for_prompt(self) -> str:
        """Format tools as text for the system prompt.

        Returns:
            Formatted tool descriptions with usage instructions
        """
        tools_text = format_tools_for_prompt(self.tools or [])
        return self._build_tool_instructions(tools_text)

    def _build_tool_descriptions(self) -> List[str]:
        """Build formatted descriptions for each tool.

        Returns:
            List of formatted tool description strings
        """
        return build_tool_descriptions(self.tools or [])

    def _format_parameters(self, params: Dict) -> List[str]:
        """Format tool parameters as strings.

        Args:
            params: Parameter definitions dictionary

        Returns:
            List of formatted parameter strings
        """
        return format_parameters(params)

    def _build_tool_instructions(self, tools_text: str) -> str:
        """Build complete tool usage instructions.

        Args:
            tools_text: Formatted tool descriptions

        Returns:
            Complete instructions with examples
        """
        return build_tool_instructions(tools_text)

    def parse_tool_calls_from_response(
        self, response_text: str
    ) -> Tuple[Optional[List[dict]], str]:
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
            return self._parse_tool_calls(response_text)

    def _parse_mistral_tool_calls(
        self, response_text: str
    ) -> Tuple[Optional[List[dict]], str]:
        """Parse tool calls from Mistral native format.

        Mistral models output tool calls in a specific format that we need to parse.

        Args:
            response_text: The model's response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        return parse_mistral_tool_calls(self, response_text)

    def _parse_json_mode_tool_calls(
        self, response_text: str
    ) -> Tuple[Optional[List[dict]], str]:
        """Parse tool calls from structured JSON mode output.

        For models like Qwen2.5, Llama-3.1, Phi-3 that can output clean JSON.
        Expected format: {"tool": "tool_name", "arguments": {...}}

        Args:
            response_text: The model's response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        return parse_json_mode_tool_calls(self, response_text)

    def _parse_tool_calls(
        self, response_text: str
    ) -> Tuple[Optional[List[dict]], str]:
        """Parse tool calls from model response (ReAct fallback format).

        Args:
            response_text: The model's response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        tool_calls, cleaned_text = parse_react_tool_calls(
            self,
            response_text,
        )
        parsed = try_parse_json_blocks(self, cleaned_text)
        if parsed is not None:
            json_tool_calls, cleaned_text = parsed
            tool_calls.extend(json_tool_calls)
        return tool_calls or None, cleaned_text
