"""Tool-parsing mixin for the GGUF chat adapter."""

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from airunner_services.llm.adapters.chat_gguf_tool_parsing import (
    extract_gpt_oss_recipient,
    extract_prefilled_gpt_oss_tool_json,
    normalize_tool_payload,
    normalize_tool_value,
    parse_gpt_oss_commentary_tool_calls,
    parse_prefilled_gpt_oss_tool_call,
    parse_react_tool_calls,
)


class ChatGGUFToolParsingMixin:
    """Provide tool-call parsing helpers for ChatGGUF."""

    def _extract_tool_calls(
        self,
        content: str,
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
        self,
        content: str,
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
        """Normalize one candidate tool payload."""
        return normalize_tool_payload(payload)

    def _normalize_tool_value(self, key: str, value: Any) -> Any:
        """Normalize one tool payload field value."""
        return normalize_tool_value(key, value)

    def _parse_gpt_oss_commentary_tool_calls(
        self,
        content: str,
    ) -> List[Dict[str, Any]]:
        """Parse Harmony commentary tool calls from one response."""
        return parse_gpt_oss_commentary_tool_calls(self, content)

    def _extract_prefilled_gpt_oss_tool_json(self, content: str) -> str:
        """Extract raw JSON from a prefilled GPT-OSS tool call."""
        return extract_prefilled_gpt_oss_tool_json(content)

    def _parse_prefilled_gpt_oss_tool_call(
        self,
        content: str,
    ) -> List[Dict[str, Any]]:
        """Parse a prefilled GPT-OSS tool call body."""
        return parse_prefilled_gpt_oss_tool_call(self, content)

    def _extract_gpt_oss_recipient(
        self,
        role_header: Optional[str],
        channel_header: str,
    ) -> Optional[str]:
        """Extract a Harmony tool recipient from parsed headers."""
        return extract_gpt_oss_recipient(role_header, channel_header)

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse text-encoded tool calls from model response text."""
        tool_calls, _ = self._extract_tool_calls(content)
        return tool_calls

    def _parse_xml_tool_calls(
        self,
        content: str,
    ) -> tuple[List[Dict[str, Any]], str]:
        """Parse XML-tagged tool calls from model response text."""
        tool_calls: List[Dict[str, Any]] = []
        pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            try:
                call_data = json.loads(match.strip())
            except json.JSONDecodeError as error:
                self.logger.warning("Failed to parse tool call JSON: %s", error)
                continue
            tool_calls.append(
                {
                    "id": str(uuid.uuid4()),
                    "name": call_data.get("name"),
                    "args": call_data.get("arguments", {}),
                    "type": "tool_call",
                }
            )
        cleaned = re.sub(
            r'<tool_call>\s*.*?\s*</tool_call>',
            "",
            content,
            flags=re.DOTALL,
        ).strip()
        return tool_calls, cleaned

    def _parse_react_tool_calls(
        self,
        content: str,
    ) -> tuple[List[Dict[str, Any]], str]:
        """Parse ReAct-style tool calls from model response text."""
        return parse_react_tool_calls(self, content)

    def _parse_native_tool_calls(
        self,
        raw_tool_calls: Optional[List[Dict[str, Any]]],
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