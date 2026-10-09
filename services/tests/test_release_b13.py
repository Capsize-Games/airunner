"""Regression tests for release issue B13 (#2143).

Proves the B13 Qt chat-stream adapter surfaces B01 companion
events (as produced by the B12 local-inference service) in the
existing Qt stream vocabulary:

- Text streams preserve message ordering, request/conversation/
  call-chain IDs, and first/last framing.
- Stale, duplicate, and foreign-chain events are dropped.
- A failed turn surfaces a retryable error and ends the turn.
- Cancellation settles the turn silently and drops late events.
- Tool calls become tool-status updates alongside the text.
- Switching/reopening a conversation settles the in-flight turn
  and restores the adapter's bot/session state.

Uses real data contracts (B12 ``RegistryInferenceClient`` over a
fake registry/runtime, real ``CompanionStreamEvent`` values) with
fake external/runtime boundaries — no model, network, GPU,
database, or GUI access.

Manual Qt steps (acceptance: do not launch a GUI in ordinary
agent validation) are listed in ``MANUAL_QT_STEPS``.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from typing import Any, Iterable, List, Optional

from airunner_services.ipc.messages import EnvelopeStatus, StreamDelta
from airunner_services.llm.companion.contracts import (
    ERROR_INFERENCE_UNAVAILABLE,
    CallChainId,
    ChatbotId,
    CompanionStreamEvent,
    SessionId,
)
from airunner_services.llm.companion.inference import (
    CompanionInferenceRequest,
)
from airunner_services.llm.companion.local_inference import (
    RegistryInferenceClient,
)
from airunner_services.llm.companion.qt_chat_adapter import (
    CompanionChatAdapter,
)
from airunner_services.llm.companion.qt_chat_chunks import (
    TEXT_SIGNAL,
    TOOL_STATUS_SIGNAL,
    chunk_signal,
    chunk_to_response_fields,
    chunk_to_tool_status_payload,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ChatMessage,
    LLMInvocationResponse,
    MessageRole,
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner_services.runtimes.registry import (
    DEFAULT_PROVIDER,
    RuntimeRegistry,
    RuntimeRoute,
)

MANUAL_QT_STEPS = (
    "1. Start the daemon and the desktop app on a Linux+NVIDIA "
    "host; open the Chat tab (real display, not offscreen).",
    "2. Send a chat message; confirm tokens stream and the turn "
    "finishes with the input re-enabled (legacy path unchanged).",
    "3. Send another message and press Stop mid-stream; confirm "
    "the stream halts, the input re-enables, and no error shows.",
    "4. From a dev console on the live widget, call "
    "begin_companion_turn('manual-1', request_id), then "
    "feed_companion_stream_events([...]) with two text events and "
    "a final event; confirm ordered tokens and a settled turn.",
    "5. Feed a FAILED companion event; confirm a visible "
    "'Error: ... (retryable)' system message ends the turn.",
    "6. Begin a turn, then switch to another conversation in the "
    "history panel; confirm the old turn settles and the new "
    "conversation loads with correct history.",
    "7. Reopen the first conversation; confirm its history "
    "reloads and a new turn streams normally.",
)


class _FakeRuntimeClient(RuntimeClient):
    """Replay canned deltas; never touches a model or network."""

    def __init__(self, deltas: Optional[list] = None) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider=DEFAULT_PROVIDER,
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
        )
        self.cancelled: List[str] = []
        self._deltas = list(deltas or [])

    def invoke(self, request: Any) -> Any:
        return LLMInvocationResponse(content="local reply")

    def stream(self, request: Any) -> Iterable[Any]:
        return list(self._deltas)

    def healthcheck(self) -> RuntimeHealth:
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=RuntimeHealthStatus.READY,
        )

    def cancel(self, request_id: str) -> Any:
        self.cancelled.append(request_id)
        return None


def _client(deltas: Optional[list] = None) -> RegistryInferenceClient:
    """Return a B12 client over a local-only fake registry."""
    registry = RuntimeRegistry()
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=DEFAULT_PROVIDER),
        _FakeRuntimeClient(deltas),
    )
    return RegistryInferenceClient(registry)


def _events(client: RegistryInferenceClient, call: str) -> list:
    """Stream one turn through the real B12 client."""

    async def _run() -> list:
        request = CompanionInferenceRequest(
            call_chain_id=CallChainId(call),
            messages=[ChatMessage(role=MessageRole.USER, content="hi")],
        )
        return [event async for event in client.stream(request)]

    return asyncio.run(_run())


def _delta(text: str, sequence: int, final: bool = False) -> StreamDelta:
    """Return one local-fallback-shaped stream delta."""
    return StreamDelta(
        request_id="r1",
        sequence=sequence,
        delta={"content": text},
        final=final,
    )


def _feed(adapter: CompanionChatAdapter, events: list) -> List[dict]:
    """Adapt every event and flatten the resulting chunks."""
    chunks: List[dict] = []
    for event in events:
        chunks.extend(adapter.adapt(event))
    return chunks


def test_text_stream_preserves_order_ids_and_first_last() -> None:
    """Ordered tokens carry every ID; first/last framing is exact."""
    events = _events(
        _client([_delta("Hel", 0), _delta("lo", 1, True)]), "chain-1"
    )
    adapter = CompanionChatAdapter()
    adapter.begin_turn(CallChainId("chain-1"), "req-1", 7)
    chunks = _feed(adapter, events)
    assert [c["message"] for c in chunks] == ["Hel", "lo"]
    for chunk in chunks:
        assert chunk["request_id"] == "req-1"
        assert chunk["conversation_id"] == 7
        assert chunk["call_chain_id"] == "chain-1"
        assert chunk_signal(chunk) == TEXT_SIGNAL
    assert chunks[0]["is_first_message"] is True
    assert chunks[0]["is_end_of_message"] is False
    assert chunks[1]["is_first_message"] is False
    assert chunks[1]["is_end_of_message"] is True
    assert [c["sequence_number"] for c in chunks] == [0, 1]
    assert adapter.active_call_chain_id is None


def test_stale_duplicate_and_foreign_events_are_dropped() -> None:
    """Replays, duplicates, and other-chain events never surface."""
    adapter = CompanionChatAdapter()
    adapter.begin_turn(CallChainId("chain-1"), "req-1", 7)

    def _event(text: str, sequence: int, call: str = "chain-1"):
        return CompanionStreamEvent(
            call_chain_id=CallChainId(call),
            sequence=sequence,
            delta_text=text,
        )

    assert adapter.adapt(_event("a", 0)) != []
    assert adapter.adapt(_event("a", 0)) == []
    assert adapter.adapt(_event("late", 0)) == []
    assert adapter.adapt(_event("foreign", 1, "chain-9")) == []
    chunks = adapter.adapt(_event("b", 1, "chain-1"))
    assert [c["message"] for c in chunks] == ["b"]


def test_failed_delta_surfaces_retryable_error_and_ends_turn() -> None:
    """A FAILED runtime delta becomes one visible retryable error."""
    events = _events(
        _client(
            [
                StreamDelta(
                    request_id="r1",
                    sequence=0,
                    final=True,
                    status=EnvelopeStatus.FAILED,
                )
            ]
        ),
        "chain-2",
    )
    adapter = CompanionChatAdapter()
    adapter.begin_turn(CallChainId("chain-2"), "req-2", 7)
    chunks = _feed(adapter, events)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["is_end_of_message"] is True
    assert chunk["is_first_message"] is True
    assert chunk["error"] is True
    assert chunk["error_code"] == ERROR_INFERENCE_UNAVAILABLE
    assert chunk["retryable"] is True
    assert chunk["message"] == (
        "Error: local inference failed mid-stream (retryable)"
    )
    fields = chunk_to_response_fields(chunk)
    assert fields["is_system_message"] is True
    assert fields["request_id"] == "req-2"
    assert adapter.active_call_chain_id is None
    assert adapter.adapt(events[0]) == []


def test_cancel_settles_turn_and_drops_late_events() -> None:
    """Cancel ends the turn silently; wrong IDs and late text drop."""
    events = _events(
        _client([_delta("a", 0), _delta("b", 1, True)]), "chain-3"
    )
    adapter = CompanionChatAdapter()
    adapter.begin_turn(CallChainId("chain-3"), "req-3", 7)
    assert adapter.adapt(events[0]) != []
    assert adapter.cancel_turn(CallChainId("other")) == []
    assert adapter.active_call_chain_id == "chain-3"
    settled = adapter.cancel_turn(CallChainId("chain-3"))
    assert len(settled) == 1
    assert settled[0]["is_end_of_message"] is True
    assert settled[0]["message"] == ""
    assert settled[0]["request_id"] == "req-3"
    assert settled[0]["conversation_id"] == 7
    assert adapter.active_call_chain_id is None
    assert adapter.adapt(events[1]) == []
    assert adapter.cancel_turn() == []


def test_cancel_without_active_turn_is_silent() -> None:
    """Cancelling an idle adapter (or widget stop) emits nothing."""
    adapter = CompanionChatAdapter()
    assert adapter.cancel_turn() == []
    assert adapter.cancel_turn(CallChainId("ghost")) == []


def test_begin_while_active_raises() -> None:
    """A second turn cannot hijack an in-flight one implicitly."""
    adapter = CompanionChatAdapter()
    adapter.begin_turn(CallChainId("chain-1"), "req-1", 7)
    try:
        adapter.begin_turn(CallChainId("chain-2"), "req-2", 7)
    except ValueError as exc:
        assert "already active" in str(exc)
    else:
        raise AssertionError("begin_turn must refuse a hijack")
    assert adapter.active_call_chain_id == "chain-1"


def test_tool_calls_become_tool_status_chunks() -> None:
    """Tool calls surface as status updates next to the text."""
    events = _events(
        _client(
            [
                StreamDelta(
                    request_id="r1",
                    sequence=0,
                    delta={
                        "content": "drawing…",
                        "tool_calls": [
                            {
                                "name": "generate_image",
                                "arguments": {"prompt": "cat"},
                            }
                        ],
                    },
                    final=True,
                )
            ]
        ),
        "chain-4",
    )
    adapter = CompanionChatAdapter()
    adapter.begin_turn(CallChainId("chain-4"), "req-4", 7)
    chunks = _feed(adapter, events)
    assert len(chunks) == 2
    tool, text = chunks
    assert chunk_signal(tool) == TOOL_STATUS_SIGNAL
    assert chunk_signal(text) == TEXT_SIGNAL
    assert text["message"] == "drawing…"
    assert text["tools"] == ["generate_image"]
    payload = chunk_to_tool_status_payload(tool)
    assert payload["tool_name"] == "generate_image"
    assert payload["query"] == '{"prompt": "cat"}'
    assert payload["status"] == "completed"
    assert payload["tool_id"] == "chain-4-0-0"
    assert payload["request_id"] == "req-4"
    assert payload["conversation_id"] == 7
    assert all(
        payload[key] for key in ("tool_id", "tool_name", "query", "status")
    )


def test_switch_conversation_settles_turn_and_restores_state() -> None:
    """Switching settles the old turn and restores bot/session."""
    events = _events(_client([_delta("a", 0)]), "chain-5")
    adapter = CompanionChatAdapter(
        chatbot_id=ChatbotId(1), session_id=SessionId(10)
    )
    adapter.begin_turn(CallChainId("chain-5"), "req-5", 7)
    assert adapter.adapt(events[0]) != []
    settled = adapter.switch_conversation(
        8, chatbot_id=ChatbotId(2), session_id=SessionId(20)
    )
    assert len(settled) == 1
    assert settled[0]["is_end_of_message"] is True
    assert settled[0]["request_id"] == "req-5"
    assert settled[0]["conversation_id"] == 7
    assert adapter.active_call_chain_id is None
    assert adapter.conversation_id == 8
    assert adapter.bot_session == (2, 20)
    adapter.begin_turn(CallChainId("chain-6"), "req-6", 8)
    assert adapter.conversation_id == 8


def test_reopen_same_conversation_resets_in_flight_turn() -> None:
    """Reopening the current conversation settles its live turn."""
    events = _events(_client([_delta("a", 0)]), "chain-7")
    adapter = CompanionChatAdapter()
    adapter.begin_turn(CallChainId("chain-7"), "req-7", 7)
    assert adapter.adapt(events[0]) != []
    settled = adapter.switch_conversation(7)
    assert len(settled) == 1
    assert settled[0]["is_end_of_message"] is True
    assert adapter.active_call_chain_id is None
    assert adapter.conversation_id == 7
    assert adapter.adapt(events[0]) == []


def test_empty_final_still_settles_the_ui() -> None:
    """A textless final event still emits one terminal chunk."""
    adapter = CompanionChatAdapter()
    adapter.begin_turn(CallChainId("chain-8"), "req-8", 7)
    chunks = adapter.adapt(
        CompanionStreamEvent(
            call_chain_id=CallChainId("chain-8"),
            sequence=0,
            final=True,
        )
    )
    assert len(chunks) == 1
    assert chunks[0]["message"] == ""
    assert chunks[0]["is_first_message"] is True
    assert chunks[0]["is_end_of_message"] is True
    assert adapter.active_call_chain_id is None


def test_chunk_to_response_fields_mirrors_daemon_mapping() -> None:
    """Field mapping matches the daemon chunk conversion exactly."""
    adapter = CompanionChatAdapter(
        chatbot_id=ChatbotId(1), session_id=SessionId(2)
    )
    assert adapter.bot_session == (1, 2)
    fields = chunk_to_response_fields(
        {
            "message": "hi",
            "is_first_message": True,
            "is_end_of_message": False,
            "sequence_number": 3,
            "request_id": "req-9",
            "tools": ["t"],
            "message_type": "assistant",
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 6,
                "total_tokens": 11,
            },
        }
    )
    assert fields["message"] == "hi"
    assert fields["is_first_message"] is True
    assert fields["is_end_of_message"] is False
    assert fields["sequence_number"] == 3
    assert fields["request_id"] == "req-9"
    assert fields["tools"] == ["t"]
    assert fields["is_system_message"] is False
    assert fields["message_type"] == "assistant"
    assert fields["prompt_tokens"] == 5
    assert fields["completion_tokens"] == 6
    assert fields["total_tokens"] == 11


def test_adapter_import_is_free_of_qt_torch_and_sql_drivers() -> None:
    """The Qt-free adapter must stay importable without GUI/ML/SQL."""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; before = set(sys.modules); "
            "import airunner_services.llm.companion"
            ".qt_chat_adapter as m; "
            "assert m.CompanionChatAdapter is not None; "
            "after = set(sys.modules); new = after - before; "
            "markers = 'pyside6,pyqt,torch,sqlalchemy,"
            "psycopg,redis'.split(','); "
            "hits = [m for m in new for mk in markers "
            "if mk in m.lower()]; "
            "print(','.join(hits)); sys.exit(1 if hits else 0)",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_manual_qt_steps_are_present() -> None:
    """Acceptance requires manual Qt steps without GUI launch."""
    assert len(MANUAL_QT_STEPS) >= 5
    joined = " ".join(MANUAL_QT_STEPS)
    for keyword in ("Stop", "conversation", "Error"):
        assert keyword in joined
