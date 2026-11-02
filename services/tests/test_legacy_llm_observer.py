"""Bounded completion observation and request-owned cancellation tests."""

import queue
import threading

import pytest

from airunner_services.api.routes import legacy_llm_observer as observer_module
from airunner_services.api.routes.legacy_llm_observer import (
    LegacyCompletionObserver,
    completion_deadline_seconds,
)
from airunner_services.workers.llm_generate_worker import LLMGenerateWorker


def _observer(**kwargs):
    return LegacyCompletionObserver(
        "request-a", lambda reason: f"error:{reason}".encode(), **kwargs
    )


@pytest.mark.parametrize("raw", ["nan", "inf", "0", "3601", "nope"])
def test_deadline_configuration_rejects_nonfinite_or_out_of_range(monkeypatch, raw):
    monkeypatch.setenv("AIRUNNER_LLM_COMPLETION_TIMEOUT_SECONDS", raw)
    assert completion_deadline_seconds() == 300.0


def test_deadline_configuration_accepts_finite_value(monkeypatch):
    monkeypatch.setenv("AIRUNNER_LLM_COMPLETION_TIMEOUT_SECONDS", "1.25")
    assert completion_deadline_seconds() == 1.25


def test_timeout_emits_terminal_before_done_and_cancels_only_owned_request():
    cancelled = []
    observer = _observer(timeout_seconds=0.03, cancel=lambda: cancelled.append("a"))
    event = observer.next_event(timeout=0.2)
    assert event.terminal and event.failed
    assert event.payload == b"error:timeout"
    assert observer.done.is_set()
    assert cancelled == ["a"]


def test_callbacks_after_terminal_are_ignored():
    observer = _observer(timeout_seconds=1)
    callback = observer.protected(lambda data: observer.publish(text=data["text"]))
    assert observer.publish(text="answer", terminal=True)
    callback({"text": "late"})
    event = observer.next_event(timeout=0)
    assert event.text == "answer" and event.terminal
    assert observer.next_event(timeout=0) is None


def test_overflow_is_bounded_and_produces_one_error_frame():
    cancelled = []
    observer = _observer(
        timeout_seconds=1,
        max_events=1,
        max_buffered_bytes=4,
        max_total_bytes=32,
        cancel=lambda: cancelled.append(True),
    )
    assert observer.publish(text="1234")
    assert not observer.publish(text="x")
    first = observer.next_event(timeout=0)
    terminal = observer.next_event(timeout=0)
    assert first.text == "1234" and not first.terminal
    assert terminal.payload == b"error:overflow" and terminal.failed
    assert cancelled == [True]


def test_error_frame_bound_is_enforced():
    observer = LegacyCompletionObserver(
        "request-a", lambda _reason: b"x" * 4097, timeout_seconds=1
    )
    with pytest.raises(ValueError, match="exceeds its bound"):
        observer.fail("timeout")


def test_callback_registration_is_cleaned_up_when_observer_closes(monkeypatch):
    removed = []

    class Mediator:
        def unregister_pending_request(self, request_id):
            removed.append(request_id)

    monkeypatch.setattr(observer_module, "SignalMediator", Mediator)
    observer = _observer(timeout_seconds=1)
    observer.close()
    observer.close()
    assert removed == ["request-a"]


def test_dispatch_exception_is_terminal_and_cleans_registration(monkeypatch):
    removed = []

    class Mediator:
        def unregister_pending_request(self, request_id):
            removed.append(request_id)

    monkeypatch.setattr(observer_module, "SignalMediator", Mediator)
    observer = _observer(timeout_seconds=1)
    thread = observer.start_dispatch(
        lambda _callback: (_ for _ in ()).throw(RuntimeError("private")),
        lambda _data: None,
    )
    thread.join(timeout=1)
    event = observer.next_event(timeout=0)
    assert event.terminal and event.failure_reason == "dispatch_error"
    observer.close()
    assert removed == ["request-a"]


def test_disconnect_during_dispatch_retries_cancel_after_late_registration(monkeypatch):
    removed = []
    registered = threading.Event()
    release_sender = threading.Event()
    cancel_calls = []

    class Mediator:
        def unregister_pending_request(self, request_id):
            removed.append(request_id)

    monkeypatch.setattr(observer_module, "SignalMediator", Mediator)

    def cancel():
        cancel_calls.append(True)
        # First cancellation races ahead of queue registration; the retry
        # after sender returns removes the now-queued request.
        return len(cancel_calls) > 1

    observer = _observer(timeout_seconds=1, cancel=cancel)

    def sender(_callback):
        registered.set()
        release_sender.wait(1)

    thread = observer.start_dispatch(sender, lambda _data: None)
    assert registered.wait(1)
    observer.close()
    release_sender.set()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert len(cancel_calls) == 2
    assert removed == ["request-a", "request-a"]


def test_disconnect_retry_is_not_lost_when_first_cancel_is_still_running():
    sender_entered = threading.Event()
    release_sender = threading.Event()
    cancel_entered = threading.Event()
    release_cancel = threading.Event()
    cancel_calls = []

    def cancel():
        cancel_calls.append(True)
        if len(cancel_calls) == 1:
            cancel_entered.set()
            release_cancel.wait(1)
            return False
        return True

    observer = _observer(timeout_seconds=1, cancel=cancel)

    def sender(_callback):
        sender_entered.set()
        release_sender.wait(1)

    dispatch = observer.start_dispatch(sender, lambda _data: None)
    assert sender_entered.wait(1)
    closer = threading.Thread(target=observer.close)
    closer.start()
    assert cancel_entered.wait(1)
    release_sender.set()
    dispatch.join(timeout=1)
    release_cancel.set()
    closer.join(timeout=1)
    assert not dispatch.is_alive()
    assert not closer.is_alive()
    assert len(cancel_calls) == 2


def _worker():
    """Construct just queue/cancellation state, without model initialization."""
    from airunner_services.utils.application.runtime_primitives import QObject

    worker = object.__new__(LLMGenerateWorker)
    QObject.__init__(worker)
    worker._queue_lock = threading.Lock()
    worker.queue = queue.Queue()
    worker.items = {}
    worker.current_index = 0
    worker._active_request_lock = threading.RLock()
    worker._active_llm_request_id = None
    worker._cancelled_request_ids = set()
    worker._pending_llm_request = None
    worker._pending_llm_requests = {}
    worker._retry_waiting_request_ids = set()
    worker._retry_waiting_order = []
    worker._retry_enqueued_epoch = {}
    worker._download_epoch = 0
    worker._model_manager = None
    worker.logger = type("Logger", (), {"warning": lambda *_args: None})()
    return worker


def _message(request_id):
    return {
        "llm_request": True,
        "request_id": request_id,
        "request_data": {"prompt": request_id},
    }


def test_cancel_old_request_during_next_request_handoff_is_scoped():
    worker = _worker()
    cancelled_manager_ids = []
    worker._model_manager = type(
        "Manager",
        (),
        {"cancel_request": lambda _self, request_id: cancelled_manager_ids.append(request_id)},
    )()
    worker.add_to_queue(_message("old"))
    worker.add_to_queue(_message("next"))
    assert worker.get_next_item()["request_id"] == "old"
    # The worker's normal handle_message finalizer clears the completed owner
    # before it dequeues and publishes the next request as active.
    with worker._queue_lock:
        with worker._active_request_lock:
            worker._active_llm_request_id = None
    assert worker.get_next_item()["request_id"] == "next"
    assert not worker.cancel_request("old")
    assert worker._active_llm_request_id == "next"
    assert "next" not in worker._cancelled_request_ids
    assert cancelled_manager_ids == []


def test_queued_cancellation_removes_only_matching_request():
    worker = _worker()
    worker.add_to_queue(_message("keep"))
    worker.add_to_queue(_message("remove"))
    worker.add_to_queue(_message("also-keep"))
    assert worker.cancel_request("remove")
    first = worker.get_next_item()
    assert first["request_id"] == "keep"
    with worker._queue_lock:
        with worker._active_request_lock:
            worker._active_llm_request_id = None
    second = worker.get_next_item()
    assert second["request_id"] == "also-keep"


def test_pending_download_retry_cancellation_prevents_handoff():
    worker = _worker()
    message = _message("retry")
    worker._set_pending_llm_request(message)
    worker._mark_request_waiting_for_download("retry", message)
    assert worker.cancel_request("retry")
    worker._schedule_pending_llm_retries()
    assert worker.get_next_item() is None
    assert worker._pending_llm_request is None


@pytest.mark.parametrize("ending", ["timeout", "disconnect"])
def test_timeout_or_disconnect_cancels_pending_download_retry(ending):
    worker = _worker()
    message = _message("retry")
    worker._set_pending_llm_request(message)
    worker._mark_request_waiting_for_download("retry", message)
    observer = _observer(
        timeout_seconds=0.02 if ending == "timeout" else 1,
        cancel=lambda: worker.cancel_request("retry"),
    )
    if ending == "timeout":
        event = observer.next_event(timeout=0.2)
        assert event.failure_reason == "timeout"
    else:
        observer.close()
    worker._schedule_pending_llm_retries()
    assert worker.get_next_item() is None


def test_pending_download_retry_schedule_and_cancel_have_one_owner():
    worker = _worker()
    message = _message("retry")
    worker._set_pending_llm_request(message)
    worker._mark_request_waiting_for_download("retry", message)
    started = threading.Event()
    release = threading.Event()
    result = []

    def handoff():
        started.set()
        release.wait(1)
        worker._schedule_pending_llm_retries()
        result.append(worker.get_next_item())

    thread = threading.Thread(target=handoff)
    thread.start()
    assert started.wait(1)
    assert worker.cancel_request("retry")
    release.set()
    thread.join(timeout=1)
    assert result == [None]
    assert worker._active_llm_request_id is None
