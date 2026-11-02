"""Request ownership and download retry queue contracts."""

from __future__ import annotations

import queue
import threading
from types import SimpleNamespace

from airunner_common.contract_enums import LLMActionType, ModelStatus, ModelType
from airunner_services.llm.managers.mixins.request_handling_mixin import (
    RequestHandlingMixin,
)
from airunner_services.utils.application.runtime_primitives import QObject
from airunner_services.workers.llm_generate_worker import LLMGenerateWorker


def _message(request_id: str) -> dict:
    return {
        "request_id": request_id,
        "llm_request": True,
        "request_data": {"prompt": request_id},
    }


def _worker() -> LLMGenerateWorker:
    worker = object.__new__(LLMGenerateWorker)
    QObject.__init__(worker)
    worker._queue_lock = threading.Lock()
    worker.queue = queue.Queue()
    worker.items = {}
    worker.current_index = 0
    worker._pending_llm_request = None
    worker._pending_llm_requests = {}
    worker._retry_waiting_request_ids = set()
    worker._retry_waiting_order = []
    worker._retry_enqueued_epoch = {}
    worker._download_epoch = 0
    worker._active_request_lock = threading.RLock()
    worker._active_llm_request_id = None
    worker._cancelled_request_ids = set()
    worker._model_manager = None
    worker._pending_unload_request = None
    worker.logger = type(
        "Logger",
        (),
        {
            "debug": lambda *_args: None,
            "info": lambda *_args: None,
            "warning": lambda *_args: None,
            "error": lambda *_args: None,
            "exception": lambda *_args: None,
        },
    )()
    return worker


def test_queue_dequeue_cannot_replace_a_retry_owner():
    worker = _worker()
    worker._active_llm_request_id = "retry"
    worker.add_to_queue(_message("next"))

    assert worker.get_next_item() is None
    assert worker._active_llm_request_id == "retry"
    assert worker.queue.qsize() == 1

    with worker._queue_lock:
        with worker._active_request_lock:
            worker._active_llm_request_id = None
    assert worker.get_next_item()["request_id"] == "next"
    assert worker._active_llm_request_id == "next"


def test_downloader_completion_races_with_dequeue_without_replacing_owner():
    worker = _worker()
    retry = _message("retry")
    worker._active_llm_request_id = "retry"
    worker._set_pending_llm_request(retry)
    worker._mark_request_waiting_for_download("retry", retry)
    worker.add_to_queue(_message("next"))

    start = threading.Barrier(3)
    dequeued = []

    def dequeue():
        start.wait()
        dequeued.append(worker.get_next_item())

    def model_ready():
        start.wait()
        worker._schedule_pending_llm_retries()

    threads = [threading.Thread(target=dequeue), threading.Thread(target=model_ready)]
    for thread in threads:
        thread.start()
    start.wait()
    for thread in threads:
        thread.join(timeout=1)
        assert not thread.is_alive()

    assert dequeued == [None]
    assert worker._active_llm_request_id == "retry"
    assert worker.queue.qsize() == 2


def test_completion_before_retry_result_is_queued_until_worker_is_free():
    worker = _worker()
    first = _message("first")
    worker._active_llm_request_id = "first"
    worker._set_pending_llm_request(first)

    # The downloader callback only enqueues completion; it cannot start model
    # loading or generation while the first request still owns the worker.
    worker.on_huggingface_download_complete_signal(
        {"repo_id": "fixture/model", "model_path": "/unused"}
    )
    assert worker.get_next_item() is None
    assert worker._active_llm_request_id == "first"
    assert worker.queue.qsize() == 1

    # The original request reports retryable model unavailability after the
    # completion callback has queued its event.
    assert worker._mark_request_waiting_for_download("first", first) == "waiting"
    with worker._queue_lock:
        with worker._active_request_lock:
            worker._active_llm_request_id = None

    completion = worker.get_next_item()
    assert completion["_message_type"] == "download_complete"
    worker._schedule_pending_llm_retries()
    assert worker._active_llm_request_id is None

    retry = worker.get_next_item()
    assert retry["request_id"] == "first"
    assert worker._active_llm_request_id == "first"


def test_completion_before_return_replays_all_requests_on_worker_thread():
    worker = _worker()
    worker._download_dialog_showing = False
    worker._download_dialog = None
    worker._interrupted = False
    worker._pending_convert_to_gguf = False
    worker._model_manager_lock = threading.Lock()
    emitted = []
    worker.emit_signal = lambda _code, payload: emitted.append(payload)

    class Manager:
        def __init__(self):
            self.model_status = {ModelType.LLM: ModelStatus.UNLOADED}
            self.model_name = "fixture"
            self.calls = []
            self.active_calls = 0
            self.max_active_calls = 0

        def begin_request(self, _request_id):
            pass

        def handle_request(self, message, _context):
            request_id = message["request_id"]
            self.calls.append(request_id)
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
            try:
                if len(self.calls) == 1:
                    # Completion occurs before the initial request reports
                    # retry_after_download, as can happen for a fast cache hit.
                    worker.on_huggingface_download_complete_signal(
                        {"repo_id": "fixture/model", "model_path": "/unused"}
                    )
                if len(self.calls) <= 2:
                    return {
                        "response": "Error: model is not ready",
                        "error": "not ready",
                        "retry_after_download": True,
                    }
                return {"response": "ready"}
            finally:
                self.active_calls -= 1

        def load(self):
            self.model_status[ModelType.LLM] = ModelStatus.LOADED
            return True

    manager = Manager()
    worker._model_manager = manager
    first = _message("first")
    second = _message("second")
    for message in (first, second):
        message["request_data"].update(
            prompt=message["request_id"],
            action=LLMActionType.CHAT,
            llm_request=SimpleNamespace(rag_files=None),
        )
        worker.add_to_queue(message)

    original = worker.get_next_item()
    assert original["request_id"] == "first"
    worker.handle_message(original)
    assert manager.calls == ["first"]
    assert worker._active_llm_request_id is None

    queued_second = worker.get_next_item()
    assert queued_second["request_id"] == "second"
    worker.handle_message(queued_second)
    assert manager.calls == ["first", "second"]

    completion = worker.get_next_item()
    assert completion["_message_type"] == "download_complete"
    worker.handle_message(completion)
    assert worker._active_llm_request_id is None

    for request_id in ("first", "second"):
        retry = worker.get_next_item()
        assert retry["request_id"] == request_id
        worker.handle_message(retry)

    assert manager.calls == ["first", "second", "first", "second"]
    assert manager.max_active_calls == 1
    assert worker._pending_llm_requests == {}


def test_all_waiting_requests_are_requeued_once_in_order():
    worker = _worker()
    first, second = _message("first"), _message("second")
    worker._set_pending_llm_request(first)
    worker._set_pending_llm_request(second)
    assert worker._mark_request_waiting_for_download("first", first) == "waiting"
    assert worker._mark_request_waiting_for_download("second", second) == "waiting"

    worker._schedule_pending_llm_retries()
    assert [worker.get_next_item()["request_id"], worker._active_llm_request_id] == [
        "first", "first"
    ]
    with worker._queue_lock:
        with worker._active_request_lock:
            worker._active_llm_request_id = None
    assert worker.get_next_item()["request_id"] == "second"


def test_cancel_removes_only_matching_waiting_and_queued_retry():
    worker = _worker()
    first, second = _message("first"), _message("second")
    worker._set_pending_llm_request(first)
    worker._set_pending_llm_request(second)
    worker._mark_request_waiting_for_download("first", first)
    worker._mark_request_waiting_for_download("second", second)
    worker._schedule_pending_llm_retries()

    assert worker.cancel_request("first")
    assert worker.get_next_item()["request_id"] == "second"
    assert "first" not in worker._pending_llm_requests
    assert "second" in worker._pending_llm_requests


def test_retry_after_completed_download_is_terminal_not_a_loop():
    worker = _worker()
    message = _message("retry")
    worker._set_pending_llm_request(message)
    worker._mark_request_waiting_for_download("retry", message)
    worker._schedule_pending_llm_retries()
    assert worker.get_next_item()["request_id"] == "retry"

    assert worker._mark_request_waiting_for_download("retry", message) == "exhausted"
    assert "retry" not in worker._pending_llm_requests


def test_download_failure_finishes_each_waiting_request_without_global_loss():
    worker = _worker()
    responses = []
    worker.emit_signal = lambda _code, payload: responses.append(payload)
    first, second = _message("first"), _message("second")
    worker._set_pending_llm_request(first)
    worker._set_pending_llm_request(second)
    worker._mark_request_waiting_for_download("first", first)
    worker._mark_request_waiting_for_download("second", second)

    worker._fail_pending_llm_requests("fixture download failure")

    assert {payload["request_id"] for payload in responses} == {"first", "second"}
    assert all("fixture download failure" in payload["response"].message for payload in responses)
    assert worker._pending_llm_requests == {}


class _RequestManager(RequestHandlingMixin):
    def __init__(self):
        self._request_state_lock = threading.RLock()
        self._current_request_id = None
        self._interrupted = False
        self._chat_model = None
        self._workflow_manager = None

    def do_interrupt(self):
        self._interrupted = True


def test_manager_cancellation_only_interrupts_current_request():
    manager = _RequestManager()
    manager.begin_request("current")

    assert not manager.cancel_request("previous")
    assert not manager._interrupted
    assert manager.cancel_request("current")
    assert manager._interrupted

    manager.begin_request("next")
    assert not manager._interrupted
