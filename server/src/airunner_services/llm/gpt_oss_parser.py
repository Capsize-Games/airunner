"""Helpers for parsing GPT-OSS Harmony channel output."""

import json
import re
from dataclasses import dataclass

START_TOKEN = "<|start|>"
CHANNEL_TOKEN = "<|channel|>"
CONSTRAIN_TOKEN = "<|constrain|>"
MESSAGE_TOKEN = "<|message|>"
END_TOKEN = "<|end|>"
RETURN_TOKEN = "<|return|>"
CALL_TOKEN = "<|call|>"
CONTROL_TOKENS = (
    START_TOKEN,
    CHANNEL_TOKEN,
    CONSTRAIN_TOKEN,
    MESSAGE_TOKEN,
    END_TOKEN,
    RETURN_TOKEN,
    CALL_TOKEN,
)

TOOL_ARGUMENT_HINT_KEYS = {
    "file_path",
    "workspace_path",
    "pattern",
    "timeout",
    "code",
    "document_path",
    "line_number",
    "start_line",
    "end_line",
    "old_text",
    "new_text",
    "create_backup",
    "include_line_numbers",
}


def _unwrap_json_code_fence(text: str) -> str:
    """Return the body of a fenced JSON block when present."""
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        re.DOTALL,
    )
    if fenced:
        return fenced.group(1).strip()
    return text


def _ordered_keys_look_like_tool_arguments(keys: list[str]) -> bool:
    """Return True when ordered keys resemble tool arguments."""
    if not keys:
        return False

    first_key = keys[0]
    later_keys = set(keys[1:])
    if first_key in TOOL_ARGUMENT_HINT_KEYS:
        return True
    return first_key == "content" and bool(
        later_keys & TOOL_ARGUMENT_HINT_KEYS
    )


def _dict_looks_like_tool_argument_payload(payload: dict) -> bool:
    """Return True when one JSON object looks like tool arguments."""
    return _ordered_keys_look_like_tool_arguments(
        [str(key) for key in payload.keys()]
    )


def looks_like_tool_argument_payload(text: str) -> bool:
    """Return True when text looks like tool arguments, even truncated."""
    stripped = _unwrap_json_code_fence((text or "").strip())
    if not stripped or stripped[0] not in "[{":
        return False

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        keys = re.findall(
            r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:',
            stripped[:512],
        )
        return _ordered_keys_look_like_tool_arguments(keys)

    if isinstance(payload, dict):
        return _dict_looks_like_tool_argument_payload(payload)
    if isinstance(payload, list) and payload:
        return all(
            isinstance(item, dict)
            and _dict_looks_like_tool_argument_payload(item)
            for item in payload
        )
    return False


@dataclass
class GPTOSSParsedDelta:
    """One incremental GPT-OSS parser delta."""

    analysis_text: str = ""
    final_text: str = ""


@dataclass
class GPTOSSParseResult:
    """Parsed GPT-OSS assistant response."""

    thinking_content: str | None
    content: str
    raw_response: str


def has_gpt_oss_markup(text: str) -> bool:
    """Return True when Harmony control tokens appear in text."""
    return any(token in (text or "") for token in CONTROL_TOKENS)


def _split_possible_control_prefix(text: str) -> tuple[str, str]:
    """Split stable content from a trailing partial control token."""
    if not text:
        return "", ""
    last_lt = text.rfind("<")
    if last_lt == -1:
        return text, ""
    suffix = text[last_lt:]
    if any(token.startswith(suffix) for token in CONTROL_TOKENS):
        return text[:last_lt], suffix
    return text, ""


def _extract_until_control(text: str) -> tuple[str, str, bool]:
    """Read text until the next complete Harmony control token."""
    marker_index = text.find("<|")
    if marker_index == -1:
        return "", text, False
    return text[:marker_index], text[marker_index:], True


def _parse_header_section(text: str) -> tuple[str, str]:
    """Parse one Harmony header section into value and recipient."""
    parts = (text or "").split()
    if not parts:
        return "", ""

    value = parts[0].strip()
    recipient = ""
    for part in parts[1:]:
        if part.startswith("to="):
            recipient = part[3:].strip()
            break
    return value, recipient


@dataclass
class GPTOSSStreamParser:
    """Incrementally normalize GPT-OSS Harmony assistant output."""

    buffer: str = ""
    state: str = "control"
    current_role: str = "assistant"
    current_channel: str = ""
    current_recipient: str = ""

    def feed(self, fragment: str) -> GPTOSSParsedDelta:
        """Consume one raw text fragment and emit parsed assistant text."""
        delta = GPTOSSParsedDelta()
        self.buffer += fragment
        while self.buffer and self._consume(delta):
            pass
        return delta

    def finish(self) -> GPTOSSParsedDelta:
        """Flush any stable trailing content at the end of the stream."""
        delta = GPTOSSParsedDelta()
        stable, remainder = _split_possible_control_prefix(self.buffer)
        if stable:
            self._append(delta, stable)
        self.buffer = remainder
        return delta

    def _consume(self, delta: GPTOSSParsedDelta) -> bool:
        """Consume one parser step from the buffered GPT-OSS content."""
        handlers = {
            "control": self._consume_control,
            "role": self._consume_role,
            "channel": self._consume_channel,
            "constrain": self._consume_constrain,
            "content": self._consume_content,
        }
        return handlers[self.state](delta)

    def _take_token(self, token: str) -> bool:
        """Consume one exact Harmony control token when present."""
        if not self.buffer.startswith(token):
            return False
        self.buffer = self.buffer[len(token) :]
        return True

    def _consume_control(self, delta: GPTOSSParsedDelta) -> bool:
        """Consume one Harmony control token or visible fallback text."""
        if self._take_token(START_TOKEN):
            self.current_channel = ""
            self.current_recipient = ""
            self.state = "role"
            return True
        if self._take_token(CHANNEL_TOKEN):
            self.state = "channel"
            return True
        if self._take_token(CONSTRAIN_TOKEN):
            self.state = "constrain"
            return True
        if self._take_token(MESSAGE_TOKEN):
            self.state = "content"
            return True
        if (
            self._take_token(END_TOKEN)
            or self._take_token(RETURN_TOKEN)
            or self._take_token(CALL_TOKEN)
        ):
            self.current_channel = ""
            self.current_recipient = ""
            return True
        if any(token.startswith(self.buffer) for token in CONTROL_TOKENS):
            return False
        stable, remainder = _split_possible_control_prefix(self.buffer)
        if not stable:
            return False
        self.buffer = remainder
        self.state = "content"
        self._append(delta, stable)
        return True

    def _consume_role(self, _delta: GPTOSSParsedDelta) -> bool:
        """Consume the Harmony role value after a start token."""
        value, remainder, complete = _extract_until_control(self.buffer)
        if not complete:
            return False
        role, recipient = _parse_header_section(value)
        self.current_role = role or self.current_role
        self.current_recipient = recipient
        self.buffer = remainder
        self.state = "control"
        return True

    def _consume_channel(self, _delta: GPTOSSParsedDelta) -> bool:
        """Consume the Harmony channel value after a channel token."""
        value, remainder, complete = _extract_until_control(self.buffer)
        if not complete:
            return False
        channel, recipient = _parse_header_section(value)
        self.current_channel = channel
        if recipient:
            self.current_recipient = recipient
        self.buffer = remainder
        self.state = "control"
        return True

    def _consume_constrain(self, _delta: GPTOSSParsedDelta) -> bool:
        """Consume and ignore one Harmony constrain section."""
        _, remainder, complete = _extract_until_control(self.buffer)
        if not complete:
            return False
        self.buffer = remainder
        self.state = "control"
        return True

    def _consume_content(self, delta: GPTOSSParsedDelta) -> bool:
        """Consume assistant-visible content until the next control token."""
        value, remainder, complete = _extract_until_control(self.buffer)
        if not complete:
            stable, trailing = _split_possible_control_prefix(self.buffer)
            if not stable:
                return False
            self.buffer = trailing
            self._append(delta, stable)
            return True
        self.buffer = remainder
        self.state = "control"
        if value:
            self._append(delta, value)
        return True

    def _append(self, delta: GPTOSSParsedDelta, value: str) -> None:
        """Append one visible content segment to the correct output channel."""
        if self.current_role != "assistant":
            return
        if self.current_channel == "analysis":
            delta.analysis_text += value
        elif self.current_channel == "final" or not self.current_channel:
            delta.final_text += value


def parse_gpt_oss_response(raw_response: str) -> GPTOSSParseResult:
    """Parse one full GPT-OSS Harmony response into thinking and content."""
    parser = GPTOSSStreamParser()
    delta = parser.feed(raw_response or "")
    final_delta = parser.finish()
    thinking = (
        delta.analysis_text + final_delta.analysis_text
    ).strip() or None
    content = (delta.final_text + final_delta.final_text).strip()
    if not content and not thinking:
        content = (raw_response or "").strip()
    return GPTOSSParseResult(
        thinking_content=thinking,
        content=content,
        raw_response=raw_response or "",
    )
