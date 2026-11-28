"""Unit tests for the signal-client wait helpers.

_await_signal_status and _make_status_handler were extracted to keep
_wait_for_model_status within the long-function threshold. These tests
pin the timeout mapping, the custom-timeout override, and the queue
filtering rules.
"""

from queue import Queue
from unittest.mock import MagicMock

from airunner_common.contract_enums import ModelStatus

from airunner_services.runtimes.signal_runtime_client import (
    _SignalRuntimeClient,
)


def _concrete():
    class _Concrete(_SignalRuntimeClient):
        def invoke(self, request):
            raise NotImplementedError

    return _Concrete


def _make_obj(timeout=30.0):
    cls = _concrete()
    obj = cls.__new__(cls)
    obj._timeout_seconds = timeout
    obj._matches_model = MagicMock(return_value=True)
    obj._cache_status = MagicMock()
    return obj


def test_await_returns_queued_status():
    obj = _make_obj()
    queue = Queue()
    queue.put("ok")
    assert obj._await_signal_status(queue, None) == "ok"


def test_await_returns_none_on_empty_timeout():
    obj = _make_obj()
    queue = Queue()
    assert obj._await_signal_status(queue, 0.01) is None


def test_await_uses_default_timeout_when_none_given(monkeypatch):
    obj = _make_obj(timeout=5.0)
    seen = {}

    class _Q:
        def get(self, timeout):
            seen["timeout"] = timeout
            return "s"

    assert obj._await_signal_status(_Q(), None) == "s"
    assert seen["timeout"] == 5.0


def test_await_prefers_explicit_timeout(monkeypatch):
    obj = _make_obj(timeout=5.0)
    seen = {}

    class _Q:
        def get(self, timeout):
            seen["timeout"] = timeout
            return "s"

    assert obj._await_signal_status(_Q(), 1.5) == "s"
    assert seen["timeout"] == 1.5


def test_handler_queues_success_status():
    obj = _make_obj()
    queue = Queue()
    handler = obj._make_status_handler(queue, (ModelStatus.LOADED,), ModelStatus)
    handler({"model": "m", "status": ModelStatus.LOADED})
    assert queue.get_nowait() is ModelStatus.LOADED
    obj._cache_status.assert_called_once()


def test_handler_queues_failed_status():
    obj = _make_obj()
    queue = Queue()
    handler = obj._make_status_handler(queue, (ModelStatus.LOADED,), ModelStatus)
    handler({"model": "m", "status": ModelStatus.FAILED})
    assert queue.get_nowait() is ModelStatus.FAILED


def test_handler_ignores_non_matching_model():
    obj = _make_obj()
    obj._matches_model.return_value = False
    queue = Queue()
    handler = obj._make_status_handler(queue, (ModelStatus.LOADED,), ModelStatus)
    handler({"model": "other", "status": ModelStatus.LOADED})
    assert queue.empty()


def test_handler_ignores_non_terminal_status():
    obj = _make_obj()
    queue = Queue()
    handler = obj._make_status_handler(queue, (ModelStatus.LOADED,), ModelStatus)
    handler({"model": "m", "status": ModelStatus.LOADING})
    assert queue.empty()
