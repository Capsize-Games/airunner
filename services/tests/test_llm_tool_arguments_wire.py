"""Regression test for issue #2222.

``LLMResponse.tool_arguments`` was permanently ``None``: the
services-side tool-status emitter never included call arguments in
its event dict, and ``tool_status_stream_payload`` never copied them
onto the NDJSON wire, even though the desktop converter already read
``chunk.get("tool_arguments")``. These tests pin the full round
trip: emitter -> wire payload -> NDJSON bytes -> parsed chunk ->
desktop ``LLMResponse.tool_arguments``.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage

from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.enums import LLMActionType
from airunner_services.api.routes.legacy_llm_helpers import (
    tool_status_stream_payload,
)
from airunner_services.api.routes.legacy_llm_stream_payloads import (
    ndjson_line,
)
from airunner_services.llm.managers.mixins.tool_execution_mixin import (
    ToolExecutionMixin,
)

_TOOL_ARGS = {"query": "capsize games", "max_results": 3}
_TOOL_CALLS = [{"name": "search_web", "args": _TOOL_ARGS, "id": "call-1"}]


class _CapturingSink:
    """Workflow event sink that records tool-status payloads."""

    active = True

    def __init__(self) -> None:
        """Initialize the empty capture list."""
        self.events: list[dict[str, Any]] = []

    def emit_tool_status(self, payload: dict[str, Any]) -> None:
        """Record one tool-status payload."""
        self.events.append(payload)

    def emit_thinking(self, payload: dict[str, Any]) -> None:
        """Ignore one thinking payload."""
        del payload

    def emit_bot_mood(self, payload: dict[str, Any]) -> None:
        """Ignore one bot-mood payload."""
        del payload


class _Harness(ToolExecutionMixin):
    """Minimal mixin owner with a capturing event sink."""

    def __init__(self) -> None:
        """Initialize the mixin with a capturing sink."""
        super().__init__()
        self._event_sink = _CapturingSink()
        self._current_request_id = "req-1"


def _wire_chunk(event: dict[str, Any]) -> dict[str, Any]:
    """Serialize one event to NDJSON and parse it back to a chunk."""
    payload = tool_status_stream_payload(event)
    assert payload is not None
    return json.loads(ndjson_line(payload).decode("utf-8"))


def test_starting_status_emits_tool_arguments() -> None:
    """The starting event must carry the tool call's arguments."""
    harness = _Harness()
    harness._emit_starting_status(_TOOL_CALLS)
    assert harness._event_sink.events[0]["tool_arguments"] == _TOOL_ARGS


def test_completed_status_emits_tool_arguments() -> None:
    """The completed event must carry the tool call's arguments."""
    harness = _Harness()
    message = ToolMessage(content="done", tool_call_id="call-1")
    harness._emit_completed_status({"messages": [message]}, _TOOL_CALLS)
    assert harness._event_sink.events[0]["tool_arguments"] == _TOOL_ARGS


def test_wire_payload_carries_tool_arguments() -> None:
    """The NDJSON wire payload must forward tool arguments."""
    harness = _Harness()
    harness._emit_starting_status(_TOOL_CALLS)
    chunk = _wire_chunk(harness._event_sink.events[0])
    assert chunk["tool_arguments"] == _TOOL_ARGS


def test_wire_payload_defaults_tool_arguments_to_none() -> None:
    """Events without arguments (tool selection) must stay valid."""
    payload = tool_status_stream_payload(
        {
            "tool_id": "sel-1",
            "tool_name": "tool_analyzer",
            "query": "hi",
            "status": "completed",
        }
    )
    assert payload is not None
    assert payload["tool_arguments"] is None


def test_round_trip_to_desktop_response() -> None:
    """Wire tool arguments must reach LLMResponse.tool_arguments."""
    harness = _Harness()
    harness._emit_starting_status(_TOOL_CALLS)
    chunk = _wire_chunk(harness._event_sink.events[0])
    response = LLMAPIService._response_from_daemon_chunk(
        chunk,
        request_id="req-1",
        action=LLMActionType.CHAT,
        node_id=None,
    )
    assert response.tool_arguments == _TOOL_ARGS
