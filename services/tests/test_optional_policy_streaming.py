"""Behavior tests for the default, disabled content-policy stream mode."""

from __future__ import annotations

import logging
from types import SimpleNamespace

from airunner_services.llm.managers.mixins.generation_stream_support import (
    create_streaming_callback,
    send_end_of_message,
)


def _owner(signals: list, *, interrupted: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        api=SimpleNamespace(
            llm=SimpleNamespace(send_llm_text_streamed_signal=signals.append)
        ),
        logger=logging.getLogger(__name__),
        _current_request_id="request-optional-policy",
        _workflow_manager=SimpleNamespace(_assistant_turn_index=4),
        _interrupted=interrupted,
    )


def test_disabled_policy_forwards_each_token_before_end(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AIRUNNER_CONTENT_POLICY_MODE", "disabled")
    signals: list = []
    owner = _owner(signals)
    request = SimpleNamespace(node_id="node-optional-policy")
    complete = [""]
    sequence = [0]

    on_token = create_streaming_callback(owner, request, complete, sequence)
    on_token("Assistant: ")
    assert signals == []
    on_token("Hello ")
    assert [signal.message for signal in signals] == ["Hello "]
    on_token("world")

    assert [signal.message for signal in signals] == ["Hello ", "world"]
    assert complete == ["Hello world"]
    assert [signal.sequence_number for signal in signals] == [1, 2]
    assert [signal.is_first_message for signal in signals] == [True, False]
    assert all(signal.node_id == request.node_id for signal in signals)
    assert all(signal.request_id == owner._current_request_id for signal in signals)
    assert all(signal.message_type == "assistant" for signal in signals)
    assert all(signal.turn_index == 4 for signal in signals)

    send_end_of_message(owner, request, sequence, [], 2, 2, 4, complete[0])

    assert len(signals) == 3
    assert signals[-1].is_end_of_message is True
    assert signals[-1].sequence_number == 3
    assert signals[-1].final_visible_message == "Hello world"
    assert [signal.message for signal in signals[:-1]] == ["Hello ", "world"]


def test_disabled_policy_fallback_emits_once_before_end(monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_CONTENT_POLICY_MODE", "disabled")
    signals: list = []
    owner = _owner(signals)
    request = SimpleNamespace(node_id="node-fallback")

    send_end_of_message(
        owner,
        request,
        [0],
        [],
        1,
        2,
        3,
        "final-only response",
    )

    assert len(signals) == 2
    assert signals[0].message == "final-only response"
    assert signals[0].is_end_of_message is False
    assert signals[0].sequence_number == 1
    assert signals[1].is_end_of_message is True
    assert signals[1].sequence_number == 2
    assert signals[1].final_visible_message == "final-only response"


def test_disabled_policy_interruption_stops_later_tokens(monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_CONTENT_POLICY_MODE", "disabled")
    signals: list = []
    owner = _owner(signals)
    request = SimpleNamespace(node_id="node-cancel")
    complete = [""]
    sequence = [0]
    on_token = create_streaming_callback(owner, request, complete, sequence)

    owner._interrupted = True
    on_token("discard after cancel")

    assert signals == []
    assert complete == [""]
    send_end_of_message(owner, request, sequence, [], 0, 0, 0, "discard after cancel")
    assert len(signals) == 1
    assert signals[0].is_end_of_message is True
    assert not signals[0].message
    assert not signals[0].final_visible_message
