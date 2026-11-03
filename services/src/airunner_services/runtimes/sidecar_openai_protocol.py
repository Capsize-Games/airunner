"""OpenAI-compatible response parsing for the supervised LLM sidecar."""

from __future__ import annotations

import json
from typing import Any, Iterable, Iterator

from airunner_services.runtimes.message_envelopes import load_message_types


class SidecarRequestError(RuntimeError):
    """A sidecar protocol failure with a client-safe message."""

    def __init__(self, public_message: str) -> None:
        super().__init__(public_message)
        self.public_message = public_message


def decode_completion_json(response: Any) -> dict[str, Any]:
    """Decode and validate a non-streaming OpenAI-compatible completion."""
    raw = response.read()
    if not raw or not raw.strip():
        raise SidecarRequestError(
            "The local LLM sidecar returned an empty response"
        )
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("choices"), list):
        raise SidecarRequestError(
            "The local LLM sidecar returned an invalid completion"
        )
    if not data["choices"]:
        raise SidecarRequestError(
            "The local LLM sidecar returned no completion choices"
        )
    return data


def completion_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize one provider completion into AIRunner's neutral payload."""
    if data.get("error") is not None:
        raise SidecarRequestError(
            "The local LLM sidecar reported a generation error"
        )
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise SidecarRequestError(
            "The local LLM sidecar returned no completion choices"
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        raise SidecarRequestError(
            "The local LLM sidecar returned an invalid completion"
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        raise SidecarRequestError(
            "The local LLM sidecar returned an invalid completion"
        )
    content = message.get("content")
    if content is None:
        content = ""
    tools = message.get("tool_calls")
    if tools is None:
        tools = []
    finish_reason = choice.get("finish_reason")
    usage = data.get("usage")
    if usage is None:
        usage = {}
    if (
        not isinstance(content, str)
        or not isinstance(tools, list)
        or any(not isinstance(tool, dict) for tool in tools)
        or (finish_reason is not None and not isinstance(finish_reason, str))
        or not isinstance(usage, dict)
    ):
        raise SidecarRequestError(
            "The local LLM sidecar returned an invalid completion"
        )
    if not content and not tools and not finish_reason:
        raise SidecarRequestError(
            "The local LLM sidecar returned an empty completion"
        )
    return {
        "content": content,
        "tools": tools,
        "usage": usage,
        "finish_reason": finish_reason or "stop",
    }


def _read_sse_payload(response: Any) -> bytes | None:
    """Return the next data payload, or ``None`` at the DONE marker."""
    while True:
        line = response.readline()
        if not line:
            raise SidecarRequestError(
                "The local LLM sidecar stream ended unexpectedly"
            )
        if not line.startswith(b"data:"):
            continue
        payload = line.split(b":", 1)[1].strip()
        return None if payload == b"[DONE]" else payload


def _validate_sse_choice(choice: Any) -> bool:
    """Validate the first provider choice and report meaningful output."""
    if not isinstance(choice, dict):
        raise SidecarRequestError(
            "The local LLM sidecar returned malformed stream data"
        )
    finish_reason = choice.get("finish_reason")
    delta = choice.get("delta")
    text = choice.get("text")
    if delta is not None and not isinstance(delta, dict):
        raise SidecarRequestError(
            "The local LLM sidecar returned malformed stream data"
        )
    if text is not None and not isinstance(text, str):
        raise SidecarRequestError(
            "The local LLM sidecar returned malformed stream data"
        )
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise SidecarRequestError(
            "The local LLM sidecar returned malformed stream data"
        )
    has_content = False
    if delta is not None:
        content = delta.get("content")
        tool_calls = delta.get("tool_calls")
        if (
            content is not None and not isinstance(content, str)
        ) or (
            tool_calls is not None
            and (
                not isinstance(tool_calls, list)
                or any(not isinstance(call, dict) for call in tool_calls)
            )
        ):
            raise SidecarRequestError(
                "The local LLM sidecar returned malformed stream data"
            )
        has_content = bool(content or tool_calls)
    return has_content or bool(text) or finish_reason is not None


def _parse_sse_event(payload: bytes) -> tuple[dict[str, Any], bool]:
    """Decode one provider data payload and validate its schema."""
    try:
        data = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SidecarRequestError(
            "The local LLM sidecar returned malformed stream data"
        ) from exc
    if not isinstance(data, dict) or data.get("error") is not None:
        raise SidecarRequestError(
            "The local LLM sidecar reported a generation error"
        )
    choices = data.get("choices")
    if not isinstance(choices, list):
        raise SidecarRequestError(
            "The local LLM sidecar returned malformed stream data"
        )
    usage = data.get("usage")
    if "usage" in data and not isinstance(usage, dict):
        raise SidecarRequestError(
            "The local LLM sidecar returned malformed stream data"
        )
    if not choices:
        if not isinstance(usage, dict):
            raise SidecarRequestError(
                "The local LLM sidecar returned malformed stream data"
            )
        return data, False
    return data, _validate_sse_choice(choices[0])


def iter_openai_sse(response: Any) -> Iterator[dict[str, Any]]:
    """Yield validated provider data events and require completion before DONE."""
    completed = False
    while True:
        payload = _read_sse_payload(response)
        if payload is None:
            if not completed:
                raise SidecarRequestError(
                    "The local LLM sidecar ended without a completion"
                )
            return
        data, event_completed = _parse_sse_event(payload)
        completed = completed or event_completed
        yield data


def stream_deltas(request_id: str, response: Any) -> Iterable[Any]:
    """Convert validated provider SSE events to neutral stream deltas."""
    messages = load_message_types()
    sequence = 0
    usage: dict[str, Any] | None = None
    for data in iter_openai_sse(response):
        event_usage = data.get("usage")
        if event_usage is not None:
            usage = event_usage
        choices = data["choices"]
        if not choices:
            continue
        choice = choices[0]
        delta = choice.get("delta") or {}
        chunk: dict[str, Any] = {}
        content = delta.get("content")
        tool_calls = delta.get("tool_calls")
        finish_reason = choice.get("finish_reason")
        if content:
            chunk["content"] = content
        if tool_calls:
            chunk["tool_calls"] = tool_calls
        if finish_reason is not None:
            chunk["finish_reason"] = finish_reason
        yield messages.StreamDelta(
            request_id=request_id,
            sequence=sequence,
            delta=chunk,
            final=False,
            metadata={"usage": usage} if usage is not None else {},
        )
        sequence += 1
    yield messages.StreamDelta(
        request_id=request_id,
        sequence=sequence,
        final=True,
        metadata={"usage": usage} if usage is not None else {},
    )
