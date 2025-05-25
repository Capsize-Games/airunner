"""
Unit tests for SignalMediator and Signal in signal_mediator.py.
Covers registration, emission, and backend delegation.
"""

import pytest
from unittest.mock import MagicMock
from airunner.utils.application.signal_mediator import SignalMediator, Signal
from airunner.enums import SignalCode


class DummyBackend:
    def __init__(self):
        self.registered = []
        self.emitted = []

    def register(self, code, func):
        self.registered.append((code, func))

    def emit_signal(self, code, data):
        self.emitted.append((code, data))


def test_signal_mediator_register_and_emit(monkeypatch):
    mediator = SignalMediator()
    called = {}

    def slot(data):
        called["data"] = data

    mediator.register(SignalCode.CLEAR_PROMPTS, slot)
    mediator.emit_signal(SignalCode.CLEAR_PROMPTS, {"foo": 42})
    assert called["data"] == {"foo": 42}


def test_signal_mediator_emit_no_data(monkeypatch):
    mediator = SignalMediator()
    called = {}

    def slot(data):
        called["data"] = data

    mediator.register(SignalCode.LLM_MODEL_CHANGED, slot)
    mediator.emit_signal(SignalCode.LLM_MODEL_CHANGED)
    assert called["data"] == {}


def test_signal_mediator_with_backend():
    # Clear the SingletonMeta cache to ensure a fresh instance
    from airunner.utils.application.signal_mediator import SingletonMeta

    SingletonMeta._instances.pop(SignalMediator, None)
    backend = DummyBackend()
    mediator = SignalMediator(backend=backend)

    def slot(data):
        pass

    mediator.register(SignalCode.CLEAR_PROMPTS, slot)
    assert (SignalCode.CLEAR_PROMPTS, slot) in backend.registered
    mediator.emit_signal(SignalCode.CLEAR_PROMPTS, {"bar": 1})
    assert (SignalCode.CLEAR_PROMPTS, {"bar": 1}) in backend.emitted


def test_signal_callback_param_count():
    # slot with no params
    called = {"flag": False}

    def slot():
        called["flag"] = True

    s = Signal(slot)
    s.signal.emit({})
    assert called["flag"]
    # slot with one param
    called2 = {"val": None}

    def slot2(data):
        called2["val"] = data

    s2 = Signal(slot2)
    s2.signal.emit({"x": 1})
    assert called2["val"] == {"x": 1}


def test_signal_callback_exception(capfd):
    def slot(data):
        raise ValueError("fail")

    s = Signal(slot)
    # Should not raise, just print error
    s.signal.emit({"bad": 1})
    out, err = capfd.readouterr()
    assert (
        "Error in signal callback" in out or "Error in signal callback" in err
    )
