import pytest

from airunner.utils.application.signal_mediator import SignalMediator
from airunner.enums import SignalCode


def test_register_dedupe_and_unregister_function_callback():
    # Ensure we start fresh
    mediator = SignalMediator()
    mediator.signals = {}

    called = []

    def cb(data):
        called.append(data)

    mediator.register(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, cb)
    # Duplicate registration should be skipped
    mediator.register(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, cb)
    assert (
        len(mediator.signals[SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL]) == 1
    )

    mediator.emit_signal(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, {"a": 1})
    assert called == [{"a": 1}]

    # Unregister and ensure no handlers remain
    mediator.unregister(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, cb)
    assert (
        len(
            mediator.signals.get(
                SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, []
            )
        )
        == 0
    )


class Dummy:
    def __init__(self):
        self.called = []

    def cb(self, data):
        self.called.append(data)


def test_register_dedupe_bound_method():
    mediator = SignalMediator()
    mediator.signals = {}

    d1 = Dummy()
    d2 = Dummy()

    mediator.register(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, d1.cb)
    # Registering a different instance's method should add a second handler
    mediator.register(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, d2.cb)

    assert (
        len(mediator.signals[SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL]) == 2
    )

    # Duplicate registration on the same instance should be skipped
    mediator.register(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, d1.cb)
    assert (
        len(mediator.signals[SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL]) == 2
    )

    mediator.emit_signal(
        SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, {"k": "v"}
    )
    assert d1.called == [{"k": "v"}]
    assert d2.called == [{"k": "v"}]

    # Unregister one instance
    mediator.unregister(SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, d1.cb)
    assert (
        len(mediator.signals[SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL]) == 1
    )
    mediator.emit_signal(
        SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, {"k": "v2"}
    )
    assert d1.called == [{"k": "v"}]
    assert d2.called == [{"k": "v"}, {"k": "v2"}]

    def test_worker_manager_registers_once():
        mediator = SignalMediator()
        mediator.signals = {}

        from airunner.components.application.gui.windows.main.worker_manager import (
            WorkerManager,
        )

        wm = WorkerManager()
        # Count how many wrappers registered for the LLM_TEXT_GENERATE_REQUEST_SIGNAL
        wrappers = mediator.signals.get(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, []
        )
        matches = [w for w in wrappers if w.matches(wm.on_llm_request_signal)]
        assert len(matches) == 1
