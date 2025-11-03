"""Tool calling operations for HuggingFace chat models."""

import json
import re
import uuid
from typing import List, Optional, Dict, Tuple


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

        For Mistral native mode, tools are encoded in the tokenization,
        so we return empty string to avoid duplicate tool descriptions.

        Returns:
            Formatted tool descriptions or empty string if no tools bound or using native
        """
        if self.use_mistral_native:
            return ""

        return self._format_tools_for_prompt() if self.tools else ""

    def _format_tools_for_prompt(self) -> str:
        """Format tools as text for the system prompt.

        Returns:
            Formatted tool descriptions with usage instructions
        """
        if not self.tools:
            return ""

        tool_strings = self._build_tool_descriptions()
        tools_text = "\n\n".join(tool_strings)
        return self._build_tool_instructions(tools_text)

    def _build_tool_descriptions(self) -> List[str]:
        """Build formatted descriptions for each tool.

        Returns:
            List of formatted tool description strings
        """
        tool_strings = []
        for tool in self.tools:
            tool_str = f"- {tool['function']['name']}: {tool['function']['description']}"
            params = (
                tool["function"].get("parameters", {}).get("properties", {})
            )
            if params:
                param_strs = self._format_parameters(params)
                tool_str += "\n" + "\n".join(param_strs)
            tool_strings.append(tool_str)
        return tool_strings

    def _format_parameters(self, params: Dict) -> List[str]:
        """Format tool parameters as strings.

        Args:
            params: Parameter definitions dictionary

        Returns:
            List of formatted parameter strings
        """
        param_strs = []
        for param_name, param_info in params.items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            param_strs.append(f"  - {param_name} ({param_type}): {param_desc}")
        return param_strs

    def _build_tool_instructions(self, tools_text: str) -> str:
        """Build complete tool usage instructions.

        Args:
            tools_text: Formatted tool descriptions

        Returns:
            Complete instructions with examples
        """
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
        tool_calls = []
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

        cleaned_text = re.sub(
            tool_call_pattern, "", response_text, flags=re.DOTALL
        ).strip()

        return (tool_calls if tool_calls else None, cleaned_text)

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
        print(
            f"[JSON PARSE DEBUG] Parsing response of length {len(response_text)}",
            flush=True,
        )
        print(
            f"[JSON PARSE DEBUG] First 500 chars: {response_text[:500]}",
            flush=True,
        )

        response_text = self._fix_json_quotes(response_text)

        # Try parsing entire response as JSON first
        parsed = self._try_parse_entire_response(response_text)
        if parsed:
            return parsed

        # Try JSON code blocks
        parsed = self._try_parse_json_blocks(response_text)
        if parsed:
            return parsed

        # Try embedded JSON
        parsed = self._try_parse_embedded_json(response_text)
        if parsed:
            return parsed

        return (None, response_text.strip())

    def _fix_json_quotes(self, text: str) -> str:
        """Fix single quotes in JSON to double quotes.

        Args:
            text: Text with potential single-quote JSON

        Returns:
            Text with fixed quotes
        """
        if "{'tool'" in text or '{"tool":' not in text:
            print(
                "[JSON PARSE DEBUG] Attempting to fix single-quote JSON...",
                flush=True,
            )
            text_fixed = (
                text.replace("':", '":')
                .replace(": '", ': "')
                .replace("', '", '", "')
                .replace("'}", '"}')
            )
            if text_fixed != text:
                print(
                    "[JSON PARSE DEBUG] Fixed some single quotes, retrying parse...",
                    flush=True,
                )
                return text_fixed
        return text

    def _try_parse_entire_response(
        self, response_text: str
    ) -> Optional[Tuple[List[dict], str]]:
        """Try parsing entire response as JSON.

        Args:
            response_text: Text to parse

        Returns:
            (tool_calls, cleaned_text) tuple or None if parsing failed
        """
        try:
            print(
                "[JSON PARSE DEBUG] Attempting to parse entire response as JSON...",
                flush=True,
            )
            data = json.loads(response_text.strip())

            if isinstance(data, dict) and ("tool" in data or "name" in data):
                tool_calls = [self._extract_tool_call(data)]
                print(
                    f"[JSON PARSE DEBUG] ✓ Parsed entire response as JSON tool call: {tool_calls[0]['name']}",
                    flush=True,
                )
                return (tool_calls, "")

            elif isinstance(data, list):
                tool_calls = self._extract_tool_calls_from_list(data)
                if tool_calls:
                    print(
                        f"[JSON PARSE DEBUG] ✓ Parsed {len(tool_calls)} tool calls from array",
                        flush=True,
                    )
                    return (tool_calls, "")

        except json.JSONDecodeError as e:
            print(f"[JSON PARSE DEBUG] JSON parse failed: {e}", flush=True)
            # Try Python literal_eval fallback
            return self._try_python_literal_eval(response_text)

        return None

    def _try_python_literal_eval(
        self, response_text: str
    ) -> Optional[Tuple[List[dict], str]]:
        """Try parsing using Python's ast.literal_eval.

        Args:
            response_text: Text to parse

        Returns:
            (tool_calls, cleaned_text) tuple or None if parsing failed
        """
        print(
            "[JSON PARSE DEBUG] Attempting Python ast.literal_eval fallback...",
            flush=True,
        )
        try:
            import ast

            data = ast.literal_eval(response_text.strip())
            if isinstance(data, dict) and ("tool" in data or "name" in data):
                tool_calls = [self._extract_tool_call(data)]
                print(
                    f"[JSON PARSE DEBUG] ✓ Parsed Python-style dict as tool call: {tool_calls[0]['name']}",
                    flush=True,
                )
                return (tool_calls, "")
        except (ValueError, SyntaxError) as ast_error:
            print(
                f"[JSON PARSE DEBUG] Python literal_eval also failed: {ast_error}",
                flush=True,
            )
        return None

    def _extract_tool_call(self, data: dict) -> dict:
        """Extract tool call from data dictionary.

        Args:
            data: Dictionary with tool information

        Returns:
            Tool call dictionary
        """
        tool_name = data.get("tool") or data.get("name")
        tool_args = data.get("arguments", {})
        return {
            "name": tool_name,
            "args": tool_args,
            "id": str(uuid.uuid4()),
        }

    def _extract_tool_calls_from_list(self, data: list) -> List[dict]:
        """Extract tool calls from list of dictionaries.

        Args:
            data: List of tool data dictionaries

        Returns:
            List of tool call dictionaries
        """
        tool_calls = []
        for item in data:
            if isinstance(item, dict) and ("tool" in item or "name" in item):
                tool_calls.append(self._extract_tool_call(item))
        return tool_calls

    def _try_parse_json_blocks(
        self, response_text: str
    ) -> Optional[Tuple[List[dict], str]]:
        """Try extracting JSON from code blocks.

        Args:
            response_text: Text to parse

        Returns:
            (tool_calls, cleaned_text) tuple or None if no blocks found
        """
        json_block_pattern = r"```json\s*(\{[^`]+\})\s*```"
        matches = re.findall(json_block_pattern, response_text, re.DOTALL)

        tool_calls = []
        for match in matches:
            try:
                data = json.loads(match)
                if "tool" in data or "name" in data:
                    tool_calls.append(self._extract_tool_call(data))
                    print(
                        f"✓ Parsed JSON block tool call: {tool_calls[-1]['name']}"
                    )
            except json.JSONDecodeError as e:
                print(f"⚠ Failed to parse JSON block: {e}")
                continue

        if tool_calls:
            cleaned_text = re.sub(
                json_block_pattern, "", response_text, flags=re.DOTALL
            ).strip()
            return (tool_calls, cleaned_text)

        return None

    def _try_parse_embedded_json(
        self, response_text: str
    ) -> Optional[Tuple[List[dict], str]]:
        """Try extracting JSON objects embedded in text.

        Args:
            response_text: Text to parse

        Returns:
            (tool_calls, cleaned_text) tuple or None if no JSON found
        """
        json_pattern = r'\{(?:[^{}]|(\{(?:[^{}]|\{[^{}]*\})*\}))*(?:"tool"|"name")(?:[^{}]|(\{(?:[^{}]|\{[^{}]*\})*\}))*\}'

        tool_calls = []
        cleaned_text = response_text

        for match in re.finditer(json_pattern, response_text, re.DOTALL):
            json_str = match.group(0)
            try:
                data = json.loads(json_str)
                if "tool" in data or "name" in data:
                    tool_calls.append(self._extract_tool_call(data))
                    self.logger.debug(
                        f"Parsed embedded JSON tool call: {tool_calls[-1]['name']}"
                    )
                    cleaned_text = cleaned_text.replace(json_str, "").strip()
            except json.JSONDecodeError:
                continue

        if tool_calls:
            return (tool_calls, cleaned_text)

        return None

    def _parse_tool_calls(
        self, response_text: str
    ) -> Tuple[Optional[List[dict]], str]:
        """Parse tool calls from model response (ReAct fallback format).

        Args:
            response_text: The model's response text

        Returns:
            Tuple of (tool_calls list or None, cleaned response text)
        """
        tool_calls = []
        json_pattern = r"```json\s*(\{[^`]+\})\s*```"
        matches = re.findall(json_pattern, response_text, re.DOTALL)

        for match in matches:
            try:
                tool_data = json.loads(match)
                if "tool" in tool_data or "name" in tool_data:
                    tool_calls.append(self._extract_tool_call(tool_data))
            except json.JSONDecodeError:
                continue

        cleaned_text = re.sub(
            json_pattern, "", response_text, flags=re.DOTALL
        ).strip()

        return (tool_calls if tool_calls else None, cleaned_text)
