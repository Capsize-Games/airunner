"""
Unit tests for SignalMediator and Signal in signal_mediator.py.
Covers registration, emission, and backend delegation.
"""

import pytest
from unittest.mock import MagicMock
from airunner.utils.application.signal_mediator import SignalMediator, Signal
from airunner.enums import SignalCode
from PySide6.QtCore import QCoreApplication
import time


class DummyBackend:
    def __init__(self):
        self.registered = []
        self.emitted = []

    def register(self, code, func):
        self.registered.append((code, func))

    def emit_signal(self, code, data):
        self.emitted.append((code, data))


def wait_for_key(dct, key, timeout=1.0):
    """Wait for a key to appear in a dict, up to timeout seconds."""
    start = time.time()
    while time.time() - start < timeout:
        if key in dct:
            return True
        QCoreApplication.processEvents()
        time.sleep(0.01)
    return False


def test_signal_mediator_register_and_emit(qtbot, monkeypatch):
    # Ensure a fresh SignalMediator instance (Singleton)
    from airunner.utils.application.signal_mediator import SingletonMeta

    SingletonMeta._instances.pop(SignalMediator, None)
    mediator = SignalMediator()
    called = {}

    def slot(data):
        called["data"] = data

    mediator.register(SignalCode.CLEAR_PROMPTS, slot)
    # Give the event loop a chance to process signals
    mediator.emit_signal(SignalCode.CLEAR_PROMPTS, {"foo": 42})
    qtbot.wait(50)  # Let Qt event loop process
    assert "data" in called, "Slot was not called in time"
    assert called.get("data") == {"foo": 42}


def test_signal_mediator_emit_no_data(qtbot, monkeypatch):
    from airunner.utils.application.signal_mediator import SingletonMeta

    SingletonMeta._instances.pop(SignalMediator, None)
    mediator = SignalMediator()
    called = {}

    def slot(data):
        called["data"] = data

    mediator.register(SignalCode.LLM_MODEL_CHANGED, slot)
    mediator.emit_signal(SignalCode.LLM_MODEL_CHANGED)
    qtbot.wait(50)
    assert "data" in called, "Slot was not called in time"
    assert called.get("data") == {}


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
    # Accept error output in either stdout or stderr, but also allow for PySide6 signal errors to go to sys.__stderr__
    assert (
        "Error in signal callback" in out or "Error in signal callback" in err
    )


def test_signal_param_count_exception():
    # Simulate inspect.signature raising ValueError, should default to param_count=1
    def bad_func(x):
        pass

    import airunner.utils.application.signal_mediator as signal_mediator
    import inspect as _inspect

    orig_signature = _inspect.signature
    try:
        _inspect.signature = lambda _: (_ for _ in ()).throw(ValueError)
        s = signal_mediator.Signal(bad_func)
        assert s.param_count == 1
    finally:
        _inspect.signature = orig_signature


def test_signal_on_signal_received_param_count_zero():
    called = {"flag": False}

    def slot():
        called["flag"] = True

    from airunner.utils.application.signal_mediator import Signal

    s = Signal(slot)
    s.param_count = 0  # Force branch
    s.signal.emit({})
    assert called["flag"]


def test_signal_on_signal_received_param_count_nonzero():
    called = {"data": None}

    def slot(data):
        called["data"] = data

    from airunner.utils.application.signal_mediator import Signal

    s = Signal(slot)
    s.param_count = 1  # Force branch
    s.signal.emit({"foo": 1})
    assert called["data"] == {"foo": 1}


def test_signal_repr():
    def slot(data):
        pass

    s = Signal(slot)
    r = repr(s)
    assert isinstance(r, str)
    assert "Signal" in r


def test_signal_mediator_repr():
    from airunner.utils.application.signal_mediator import SignalMediator
    from airunner.enums import SignalCode
    from airunner.utils.application.signal_mediator import SingletonMeta

    # Ensure fresh instance
    SingletonMeta._instances.pop(SignalMediator, None)
    mediator = SignalMediator()
    r = repr(mediator)
    assert isinstance(r, str)
    assert "SignalMediator" in r


def test_signal_mediator_emit_signal_no_slot():
    from airunner.utils.application.signal_mediator import SignalMediator
    from airunner.enums import SignalCode
    from airunner.utils.application.signal_mediator import SingletonMeta

    # Ensure fresh instance
    SingletonMeta._instances.pop(SignalMediator, None)
    mediator = SignalMediator()
    # No slot registered for this code
    # Should not raise
    mediator.emit_signal(SignalCode.LLM_MODEL_CHANGED, {"foo": 1})


def test_signal_mediator_register_duplicate():
    from airunner.utils.application.signal_mediator import SignalMediator
    from airunner.enums import SignalCode
    from airunner.utils.application.signal_mediator import SingletonMeta

    # Ensure fresh instance
    SingletonMeta._instances.pop(SignalMediator, None)
    mediator = SignalMediator()
    called = {}

    def slot(data):
        called["data"] = data

    mediator.register(SignalCode.CLEAR_PROMPTS, slot)
    # Registering again should not raise
    mediator.register(SignalCode.CLEAR_PROMPTS, slot)
