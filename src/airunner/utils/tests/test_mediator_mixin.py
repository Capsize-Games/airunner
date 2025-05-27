"""
Unit tests for MediatorMixin in mediator_mixin.py.
Covers initialization, signal registration, and emit/register delegation.
"""

import pytest
from unittest.mock import MagicMock, patch
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.enums import SignalCode


class DummyMediator:
    def __init__(self, backend=None):
        self.emitted = []
        self.registered = []

    def emit_signal(self, code, data=None):
        self.emitted.append((code, data))

    def register(self, code, func):
        self.registered.append((code, func))


class DummyClass(MediatorMixin):
    def __init__(self, mediator=None):
        super().__init__(mediator=mediator)
        self.signal_handlers = {SignalCode.CLEAR_PROMPTS: self.handle_clear}
        self.register_signals()

    def handle_clear(self):
        return "cleared"


def test_mediator_mixin_emit_and_register():
    with patch(
        "airunner.utils.application.mediator_mixin.SignalMediator",
        DummyMediator,
    ):
        obj = DummyClass(mediator=None)
        # Test register_signals called in __init__
        assert (
            SignalCode.CLEAR_PROMPTS,
            obj.handle_clear,
        ) in obj.mediator.registered
        # Test emit_signal delegates
        obj.emit_signal(SignalCode.CLEAR_PROMPTS, {"foo": 1})
        assert (SignalCode.CLEAR_PROMPTS, {"foo": 1}) in obj.mediator.emitted

        # Test register delegates
        def dummy_slot():
            pass

        obj.register(SignalCode.LLM_MODEL_CHANGED, dummy_slot)
        assert (
            SignalCode.LLM_MODEL_CHANGED,
            dummy_slot,
        ) in obj.mediator.registered


def test_signal_handlers_property():
    obj = DummyClass(mediator=DummyMediator())
    # Test getter
    assert SignalCode.CLEAR_PROMPTS in obj.signal_handlers
    # Test setter
    obj.signal_handlers = {SignalCode.LLM_MODEL_CHANGED: lambda: None}
    assert SignalCode.LLM_MODEL_CHANGED in obj.signal_handlers


def test_mediator_mixin_init_with_message_backend(monkeypatch):
    import airunner.utils.application.mediator_mixin as mm_mod

    mm_mod.AIRUNNER_MESSAGE_BACKEND = '{"type": "rabbitmq", "host": "localhost"}'
    called = {}

    class DummyRabbitMQBackend:
        def __init__(self, **kwargs):
            called.update(kwargs)
            # Accept positional args for robustness

    mm_mod.RabbitMQBackend = DummyRabbitMQBackend

    class DummyMediator:
        def register(self, *a, **kw):
            pass

    mm_mod.SignalMediator = lambda backend=None: DummyMediator()
    from airunner.utils.application.mediator_mixin import MediatorMixin

    class Dummy(MediatorMixin):
        def __init__(self):
            super().__init__()

        def register_signals(self):
            pass  # Prevents call to self.register()

    Dummy()
    # Only 'host' is present in called, so check for that
    assert called.get("host") == "localhost"


def test_mediator_mixin_invalid_backend(monkeypatch):
    import airunner.utils.application.mediator_mixin as mm_mod

    mm_mod.AIRUNNER_MESSAGE_BACKEND = '{"type": "unknown"}'

    class DummyMediator:
        def register(self, *a, **kw):
            pass

    mm_mod.SignalMediator = lambda backend=None: DummyMediator()
    from airunner.utils.application.mediator_mixin import MediatorMixin

    class Dummy(MediatorMixin):
        def __init__(self):
            super().__init__()

        def register_signals(self):
            pass

    Dummy()  # Should not raise


def test_signal_handlers_property():
    from airunner.utils.application.mediator_mixin import MediatorMixin

    m = MediatorMixin.__new__(MediatorMixin)
    m._signal_handlers = {"foo": 1}
    assert m.signal_handlers == {"foo": 1}
    m.signal_handlers = {"bar": 2}
    assert m._signal_handlers == {"bar": 2}
