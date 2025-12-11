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
                        # Generate deterministic ID if not provided
                        if call.get("id"):
                            tool_id = call["id"]
                        else:
                            import hashlib
                            args = call.get("arguments", {})
                            args_str = json.dumps(args, sort_keys=True)
                            content_hash = hashlib.sha256(f"{call['name']}:{args_str}".encode()).hexdigest()[:16]
                            tool_id = f"tc-{content_hash}"
                        tool_calls.append(
                            {
                                "name": call["name"],
                                "args": call.get("arguments", {}),
                                "id": tool_id,
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
        # Try extracting JSON from <tool_call> XML tags first
        parsed = self._try_parse_tool_call_tags(response_text)
        if parsed:
            return parsed

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
            text_fixed = (
                text.replace("':", '":')
                .replace(": '", ': "')
                .replace("', '", '", "')
                .replace("'}", '"}')
            )
            if text_fixed != text:
                return text_fixed
        return text

    def _try_parse_tool_call_tags(
        self, response_text: str
    ) -> Optional[Tuple[List[dict], str]]:
        """Try extracting JSON from <tool_call> XML tags.

        Some LLMs wrap their tool call JSON in <tool_call>...</tool_call> tags.
        This method extracts the JSON from those tags and parses it.

        Args:
            response_text: Text potentially containing <tool_call> tags

        Returns:
            (tool_calls, cleaned_text) tuple or None if no tags found
        """
        # Pattern to match <tool_call>...</tool_call> tags
        tool_call_tag_pattern = r"<tool_call>\s*(\{[^<]+\})\s*</tool_call>"
        matches = re.findall(tool_call_tag_pattern, response_text, re.DOTALL)

        if not matches:
            return None

        tool_calls = []
        for match in matches:
            try:
                # Try parsing the JSON inside the tags
                json_str = match.strip()
                data = json.loads(json_str)

                # Handle both flat format and nested format
                if isinstance(data, dict):
                    # Check if it's a direct tool call with "tool"/"name" key
                    if "tool" in data or "name" in data:
                        tool_calls.append(self._extract_tool_call(data))

            except json.JSONDecodeError as e:
                self.logger.debug(
                    f"Failed to parse JSON in <tool_call> tag: {e}"
                )
                continue

        if tool_calls:
            # Remove the <tool_call> tags from the response
            cleaned_text = re.sub(
                tool_call_tag_pattern, "", response_text, flags=re.DOTALL
            ).strip()
            return (tool_calls, cleaned_text)

        # If we found tags but no valid tool calls, return the original text
        # without the tags (they might contain regular data)
        cleaned_text = re.sub(
            tool_call_tag_pattern,
            lambda m: m.group(1),
            response_text,
            flags=re.DOTALL,
        ).strip()
        return (None, cleaned_text)

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
            data = json.loads(response_text.strip())

            if isinstance(data, dict) and ("tool" in data or "name" in data):
                tool_calls = [self._extract_tool_call(data)]
                return (tool_calls, "")

            elif isinstance(data, list):
                tool_calls = self._extract_tool_calls_from_list(data)
                if tool_calls:
                    return (tool_calls, "")

        except json.JSONDecodeError as e:
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
        try:
            import ast

            data = ast.literal_eval(response_text.strip())
            if isinstance(data, dict) and ("tool" in data or "name" in data):
                tool_calls = [self._extract_tool_call(data)]
                return (tool_calls, "")
        except (ValueError, SyntaxError) as ast_error:
            self.logger.error(
                f"Failed to parse response with literal_eval: {ast_error}"
            )
        return None

    def _extract_tool_call(self, data: dict) -> dict:
        """Extract tool call from data dictionary.

        Generates a deterministic tool_call_id based on the tool name and arguments.
        This ensures that identical tool calls get the same ID, which is critical
        for LangGraph's add_messages deduplication to work properly.

        Args:
            data: Dictionary with tool information

        Returns:
            Tool call dictionary
        """
        tool_name = data.get("tool") or data.get("name")
        tool_args = data.get("arguments", {})
        
        # Generate a deterministic ID based on tool name and arguments
        # This ensures identical tool calls get the same ID for deduplication
        import hashlib
        import json as json_module
        args_str = json_module.dumps(tool_args or {}, sort_keys=True)
        content_hash = hashlib.sha256(f"{tool_name}:{args_str}".encode()).hexdigest()[:16]
        tool_call_id = f"tc-{content_hash}"
        
        return {
            "name": tool_name,
            "args": tool_args or {},
            "id": tool_call_id,
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
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON block: {e}")
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
        cleaned_text = response_text

        # First try to parse ReAct format: Action: tool_name\nAction Input: {...}
        # Note: Observation is added by LangGraph after tool execution, we don't parse it here
        # Accept both newline and inline ReAct blocks, stopping at the next Action: or string end
        react_pattern = (
            r"Action:\s*(\w+)(?:\([^)]*\))?\s*Action Input:\s*(.*?)(?=\s*Action:|$)"
        )
        react_matches = re.findall(react_pattern, response_text, re.DOTALL)

        for tool_name, raw_input in react_matches:
            # Normalize doubled braces and trim any closing tokens
            normalized = raw_input.strip().rstrip("</s> ")
            
            # Handle symmetric double braces {{...}}
            while normalized.startswith("{{") and normalized.endswith("}}") and len(normalized) > 4:
                normalized = normalized[1:-1]
            
            # Handle asymmetric extra closing braces {..."}}
            while normalized.startswith("{") and not normalized.startswith("{{") and normalized.endswith("}}"):
                normalized = normalized[:-1]
            
            # Handle asymmetric extra opening braces "{{...}
            while normalized.startswith("{{") and normalized.endswith("}") and not normalized.endswith("}}"):
                normalized = normalized[1:]

            # If the model inlined multiple actions, grab the first JSON-ish block
            if not (normalized.startswith("{") and normalized.endswith("}")):
                brace_match = re.search(r"\{.*\}", normalized, re.DOTALL)
                if brace_match:
                    normalized = brace_match.group(0).strip()

            if not (normalized.startswith("{") and normalized.endswith("}")):
                # Drop malformed tool call text entirely
                continue

            try:
                args = json.loads(normalized)
            except json.JSONDecodeError as e:
                snippet = normalized[:200].replace("\n", " ")
                self.logger.error(f"Failed to parse ReAct JSON for {tool_name}: {e} | snippet={snippet}")
                # Skip adding a tool call when JSON is broken to avoid leaking raw text
                continue

            tool_calls.append(
                {
                    "name": tool_name,
                    "args": args,
                    "id": f"call_{len(tool_calls)}",
                    "type": "tool_call",
                }
            )

        # Strip out ReAct format blocks from the response
        if react_matches:
            # Remove Action: and Action Input: lines
            cleaned_text = re.sub(
                react_pattern, "", response_text, flags=re.DOTALL
            ).strip()
            # Also remove any Observation: placeholder lines (LLM sometimes generates these)
            cleaned_text = re.sub(
                r"\n?Observation:\s*\[.*?\]", "", cleaned_text, flags=re.DOTALL
            ).strip()

        # Also try JSON code blocks as fallback
        json_pattern = r"```json\s*(\{[^`]+\})\s*```"
        json_matches = re.findall(json_pattern, cleaned_text, re.DOTALL)

        for match in json_matches:
            try:
                tool_data = json.loads(match)
                if "tool" in tool_data or "name" in tool_data:
                    tool_calls.append(self._extract_tool_call(tool_data))
            except json.JSONDecodeError:
                continue

        if json_matches:
            cleaned_text = re.sub(
                json_pattern, "", cleaned_text, flags=re.DOTALL
            ).strip()

        return (tool_calls if tool_calls else None, cleaned_text)
