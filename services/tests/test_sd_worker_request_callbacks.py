"""Unit tests for the SD worker request-callback factory.

_make_request_callbacks was extracted to keep _generate_image
within the long-function threshold. These tests pin the once-only
delivery, the finish ordering, and the error tolerance.
"""

from unittest.mock import MagicMock

from airunner_services.workers.sd_worker import SDWorker


def _make_worker():
    return SDWorker.__new__(SDWorker)


def test_complete_only_delivers_once():
    worker = _make_worker()
    delivered = []
    complete_once, finish_worker_call = worker._make_request_callbacks(
        delivered.append
    )
    complete_once("first")
    finish_worker_call()
    assert delivered == ["first"]


def test_finish_delivers_fallback_when_never_completed():
    worker = _make_worker()
    delivered = []
    complete_once, finish_worker_call = worker._make_request_callbacks(
        delivered.append
    )
    finish_worker_call("fallback")
    assert delivered == ["fallback"]


def test_complete_after_finish_does_not_double_deliver():
    worker = _make_worker()
    delivered = []
    complete_once, finish_worker_call = worker._make_request_callbacks(
        delivered.append
    )
    finish_worker_call()
    complete_once("late")
    assert delivered == [None]


def test_callback_errors_are_swallowed():
    worker = _make_worker()

    def boom(result):
        raise ValueError("nope")

    complete_once, _ = worker._make_request_callbacks(boom)
    complete_once("x")  # must not raise


def test_non_callable_original_callback_is_safe():
    worker = _make_worker()
    complete_once, finish_worker_call = worker._make_request_callbacks(None)
    complete_once("x")
    finish_worker_call("y")  # no raise, nothing delivered
