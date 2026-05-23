"""Tests for service-side LLM workflow event sinks."""

from types import SimpleNamespace

from airunner_services.contract_enums import SignalCode
from airunner_services.llm_workflow_events import (
    MediatorSignalLLMToolActionHandler,
    MediatorSignalLLMWorkflowEventSink,
    NullLLMToolActionHandler,
    NullLLMWorkflowEventSink,
    build_llm_tool_action_handler,
    build_llm_workflow_event_sink,
    resolve_llm_tool_action_handler,
    resolve_llm_workflow_event_sink,
)


def test_build_event_sink_returns_signal_adapter_when_supported():
    """One signal emitter should produce the mediator-backed adapter."""
    emitter = SimpleNamespace(emit_signal=lambda *_args, **_kwargs: None)

    sink = build_llm_workflow_event_sink(signal_emitter=emitter)

    assert isinstance(sink, MediatorSignalLLMWorkflowEventSink)
    assert sink.active is True


def test_resolve_event_sink_uses_owner_emit_signal_fallback():
    """Owners with emit_signal should resolve to the mediator adapter."""
    emitted = []

    class Owner:
        def emit_signal(self, code, data=None):
            emitted.append((code, data))

    sink = resolve_llm_workflow_event_sink(Owner())
    sink.emit_tool_status({"tool_id": "tool-1", "status": "starting"})

    assert emitted == [
        (
            SignalCode.LLM_TOOL_STATUS_SIGNAL,
            {"tool_id": "tool-1", "status": "starting"},
        )
    ]


def test_build_event_sink_defaults_to_null_sink_without_emitter():
    """Service-only callers without an emitter should get the null sink."""
    sink = build_llm_workflow_event_sink()

    assert isinstance(sink, NullLLMWorkflowEventSink)
    assert sink.active is False


def test_build_tool_action_handler_returns_signal_adapter():
    """One signal emitter should produce the tool-action adapter."""
    emitter = SimpleNamespace(emit_signal=lambda *_args, **_kwargs: None)

    handler = build_llm_tool_action_handler(signal_emitter=emitter)

    assert isinstance(handler, MediatorSignalLLMToolActionHandler)
    assert handler.active is True


def test_resolve_tool_action_handler_uses_owner_handler():
    """Owners with injected handlers should resolve them directly."""
    owner = SimpleNamespace(_tool_action_handler=NullLLMToolActionHandler())

    handler = resolve_llm_tool_action_handler(owner)

    assert isinstance(handler, NullLLMToolActionHandler)
    assert handler.active is False


def test_tool_action_handler_maps_actions_to_signals():
    """Tool actions should emit the expected compatibility signals."""
    emitted = []
    emitter = SimpleNamespace(
        emit_signal=lambda code, data=None: emitted.append((code, data))
    )
    handler = build_llm_tool_action_handler(signal_emitter=emitter)

    handled = handler.handle_action(
        "conversation_deleted",
        {"conversation_id": 7},
    )

    assert handled is True
    assert emitted == [
        (SignalCode.CONVERSATION_DELETED, {"conversation_id": 7})
    ]


def test_tool_action_handler_supports_legacy_signal_dispatch():
    """Legacy signal dispatch should still work through the adapter."""
    emitted = []
    emitter = SimpleNamespace(
        emit_signal=lambda code, data=None: emitted.append((code, data))
    )
    handler = build_llm_tool_action_handler(signal_emitter=emitter)

    handled = handler.handle_action(
        "emit_signal",
        {
            "signal_name": "LLM_CLEAR_HISTORY_SIGNAL",
            "data": {"source": "tool"},
        },
    )

    assert handled is True
    assert emitted == [
        (SignalCode.LLM_CLEAR_HISTORY_SIGNAL, {"source": "tool"})
    ]
