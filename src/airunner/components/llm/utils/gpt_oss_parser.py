"""Helpers for parsing GPT-OSS Harmony channel output."""

from dataclasses import dataclass


START_TOKEN = "<|start|>"
CHANNEL_TOKEN = "<|channel|>"
MESSAGE_TOKEN = "<|message|>"
END_TOKEN = "<|end|>"
RETURN_TOKEN = "<|return|>"
CONTROL_TOKENS = (
    START_TOKEN,
    CHANNEL_TOKEN,
    MESSAGE_TOKEN,
    END_TOKEN,
    RETURN_TOKEN,
)


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


@dataclass
class GPTOSSStreamParser:
    """Incrementally normalize GPT-OSS Harmony assistant output."""

    buffer: str = ""
    state: str = "control"
    current_role: str = "assistant"
    current_channel: str = ""

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
            "content": self._consume_content,
        }
        return handlers[self.state](delta)

    def _take_token(self, token: str) -> bool:
        """Consume one exact Harmony control token when present."""
        if not self.buffer.startswith(token):
            return False
        self.buffer = self.buffer[len(token):]
        return True

    def _consume_control(self, delta: GPTOSSParsedDelta) -> bool:
        """Consume one Harmony control token or visible fallback text."""
        if self._take_token(START_TOKEN):
            self.current_channel = ""
            self.state = "role"
            return True
        if self._take_token(CHANNEL_TOKEN):
            self.state = "channel"
            return True
        if self._take_token(MESSAGE_TOKEN):
            self.state = "content"
            return True
        if self._take_token(END_TOKEN) or self._take_token(RETURN_TOKEN):
            self.current_channel = ""
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
        self.current_role = value or self.current_role
        self.buffer = remainder
        self.state = "control"
        return True

    def _consume_channel(self, _delta: GPTOSSParsedDelta) -> bool:
        """Consume the Harmony channel value after a channel token."""
        value, remainder, complete = _extract_until_control(self.buffer)
        if not complete:
            return False
        self.current_channel = value
        self.buffer = remainder
        self.state = "control"
        return True

    def _consume_content(self, delta: GPTOSSParsedDelta) -> bool:
        """Consume one content fragment until the next control token."""
        marker_index = self.buffer.find("<|")
        if marker_index == 0:
            self.state = "control"
            return True
        if marker_index > 0:
            self._append(delta, self.buffer[:marker_index])
            self.buffer = self.buffer[marker_index:]
            return True
        stable, remainder = _split_possible_control_prefix(self.buffer)
        if not stable:
            return False
        self._append(delta, stable)
        self.buffer = remainder
        return True

    def _append(self, delta: GPTOSSParsedDelta, text: str) -> None:
        """Append parsed assistant text to analysis or final output."""
        if not text or self.current_role != "assistant":
            return
        if self.current_channel == "analysis":
            delta.analysis_text += text
            return
        if self.current_channel in ("", "final"):
            delta.final_text += text


def parse_gpt_oss_response(response: str) -> GPTOSSParseResult:
    """Normalize one GPT-OSS assistant response into thinking and final text."""
    parser = GPTOSSStreamParser()
    delta = parser.feed(response or "")
    tail = parser.finish()
    thinking_content = (delta.analysis_text + tail.analysis_text).strip()
    content = (delta.final_text + tail.final_text).strip()
    return GPTOSSParseResult(
        thinking_content=thinking_content or None,
        content=content,
        raw_response=response or "",
    )