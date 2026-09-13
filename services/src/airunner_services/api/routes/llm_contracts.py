"""Contracts for runtime-backed LLM routes."""

from __future__ import annotations

import hashlib
import os
import time
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    """Chat message submitted to the HTTP API."""

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request."""

    messages: List[ChatMessage]
    model: Optional[str] = None
    gguf_runtime_profile: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""

    content: str
    model: str
    finish_reason: str


class CompletionRequest(BaseModel):
    """Text completion request."""

    prompt: str
    gguf_runtime_profile: Optional[str] = None
    max_tokens: int = 100
    temperature: float = 0.7


class CompletionResponse(BaseModel):
    """Text completion response."""

    text: str
    finish_reason: str


class ModelInfo(BaseModel):
    """LLM model information."""

    id: str
    name: str
    loaded: bool
    size_mb: Optional[int] = None


class ModelLoadRequest(BaseModel):
    """Model load request."""

    model_id: str


class RagIndexRequest(BaseModel):
    """Document indexing request."""

    file_paths: Optional[List[str]] = None


def max_ws_message_chars() -> int:
    """Maximum characters allowed in one inbound LLM WebSocket message.

    Conservative default pending measured evidence of real prompt-length
    needs against target hardware context windows (see release issue
    S02). Override via AIRUNNER_LLM_WS_MAX_MESSAGE_CHARS.
    """
    return int(os.environ.get("AIRUNNER_LLM_WS_MAX_MESSAGE_CHARS", "16000"))


def max_ws_output_tokens() -> int:
    """Maximum ``max_tokens`` a caller may request over the LLM WebSocket.

    Override via AIRUNNER_LLM_WS_MAX_OUTPUT_TOKENS.
    """
    return int(os.environ.get("AIRUNNER_LLM_WS_MAX_OUTPUT_TOKENS", "4096"))


def default_rate_limit_max_requests() -> int:
    """Default per-principal message budget for the LLM WebSocket.

    Override via AIRUNNER_LLM_WS_RATE_LIMIT_MAX_REQUESTS.
    """
    return int(os.environ.get("AIRUNNER_LLM_WS_RATE_LIMIT_MAX_REQUESTS", "30"))


def default_rate_limit_window_seconds() -> float:
    """Sliding-window width, in seconds, for the LLM WebSocket rate limit.

    Override via AIRUNNER_LLM_WS_RATE_LIMIT_WINDOW_SECONDS.
    """
    return float(
        os.environ.get("AIRUNNER_LLM_WS_RATE_LIMIT_WINDOW_SECONDS", "60")
    )


class LLMStreamMessage(BaseModel):
    """Validated shape of one inbound ``/api/v1/llm/stream`` message.

    ``extra="forbid"``: an unrecognized field (e.g. a caller-supplied
    oversized payload stuffed into a field that isn't ``message``) must
    be rejected outright rather than silently ignored, since ignoring it
    would let arbitrary extra content bypass ``max_ws_message_chars``.
    """

    model_config = ConfigDict(extra="forbid")

    message: str
    model: Optional[str] = None
    gguf_runtime_profile: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7


class LLMStreamValidationError(ValueError):
    """A structurally valid but out-of-bounds LLM WebSocket message.

    Carries a fixed, deterministic ``code`` only; never the caller's
    message content, so it is safe to relay directly to the client.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def parse_stream_message(data: dict) -> LLMStreamMessage:
    """Parse and bound-check one inbound LLM WebSocket message.

    Raises ``pydantic.ValidationError`` for a malformed shape (wrong
    types/missing fields) and ``LLMStreamValidationError`` for a
    structurally valid message outside the configured size/token/
    temperature bounds. Neither exception embeds the message content.
    """
    parsed = LLMStreamMessage.model_validate(data)
    message = parsed.message.strip()
    if not message:
        raise LLMStreamValidationError("empty_message")
    if len(message) > max_ws_message_chars():
        raise LLMStreamValidationError("message_too_long")
    if parsed.max_tokens is None:
        # Omitted/null must resolve to a bounded default, not "no limit":
        # downstream code (llm_runtime.py) forwards this value straight
        # into the runtime's generation call, where None means unbounded
        # output rather than "use the server default" (release issue S02
        # review finding F4).
        parsed.max_tokens = max_ws_output_tokens()
    elif not (1 <= parsed.max_tokens <= max_ws_output_tokens()):
        raise LLMStreamValidationError("max_tokens_out_of_bounds")
    if not (0.0 <= parsed.temperature <= 2.0):
        raise LLMStreamValidationError("temperature_out_of_bounds")
    return parsed


class WebSocketRateLimiter:
    """Sliding-window per-principal admission control.

    Keyed by an authenticated-principal id (see ``hash_principal``), not
    the socket connection, so reconnecting with the same credential does
    not reset the caller's window. Tracked-principal count is capped
    (oldest evicted first) so a caller that varies its identity (e.g. an
    insecure-mode deployment reachable from multiple source hosts)
    cannot grow this table without bound.
    """

    _MAX_TRACKED_PRINCIPALS = 1000

    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._history: Dict[str, List[float]] = {}

    def allow(self, principal: str) -> bool:
        """Return True and record one admitted request, else False."""
        now = self._clock()
        cutoff = now - self._window_seconds
        history = self._history.get(principal)
        if history is None:
            if len(self._history) >= self._MAX_TRACKED_PRINCIPALS:
                del self._history[next(iter(self._history))]
            history = []
            self._history[principal] = history
        else:
            while history and history[0] < cutoff:
                history.pop(0)
        if len(history) >= self._max_requests:
            return False
        history.append(now)
        return True


def hash_principal(prefix: str, secret: str) -> str:
    """Return a stable, non-reversible principal id for a credential."""
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


__all__ = [
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
    "CompletionRequest",
    "CompletionResponse",
    "LLMStreamMessage",
    "LLMStreamValidationError",
    "ModelInfo",
    "ModelLoadRequest",
    "RagIndexRequest",
    "WebSocketRateLimiter",
    "default_rate_limit_max_requests",
    "default_rate_limit_window_seconds",
    "hash_principal",
    "max_ws_message_chars",
    "max_ws_output_tokens",
    "parse_stream_message",
]