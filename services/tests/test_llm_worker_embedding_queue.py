"""Worker queue contracts for daemon-owned embedding requests."""

from __future__ import annotations

import pytest
import threading

from airunner_services.runtimes.embedding_contracts import (
    EmbeddingWorkerCapacityError,
    EmbeddingWorkerUnavailableError,
)
from airunner_services.workers.llm_generate_worker import LLMGenerateWorker


def test_pending_embedding_cancellation_removes_only_its_worker_message() -> None:
    worker = LLMGenerateWorker()
    worker.running = True
    first_id, first = worker.submit_embedding_documents(["first passage"])
    second_id, second = worker.submit_embedding_documents(["second passage"])

    assert worker.cancel_embedding_request(first_id)
    assert first.cancelled()
    assert not second.cancelled()
    assert worker.queue.qsize() == 1
    remaining = worker.get_item_from_queue()
    assert remaining["request_id"] == second_id
    assert remaining["_message_type"] == "embedding"

    worker.stop()


def test_embedding_worker_caps_pending_requests_and_stops_accepting() -> None:
    worker = LLMGenerateWorker()
    worker.running = True
    requests = [
        worker.submit_embedding_documents([f"passage {index}"])
        for index in range(4)
    ]

    with pytest.raises(EmbeddingWorkerCapacityError):
        worker.submit_embedding_documents(["over capacity"])

    for request_id, future in requests:
        assert worker.cancel_embedding_request(request_id)
        assert future.cancelled()
    assert worker.queue.empty()

    worker.stop()
    with pytest.raises(EmbeddingWorkerUnavailableError):
        worker.submit_embedding_documents(["after stop"])
    assert not worker._embedding_requests


def test_shutdown_marks_active_embedding_cancelled_and_releases_request(
    monkeypatch,
) -> None:
    worker = LLMGenerateWorker()
    worker.running = True
    manager = type("Manager", (), {"runtime_activity_lock": threading.RLock()})()
    worker._model_manager = manager
    inference_started = threading.Event()
    allow_inference = threading.Event()

    class _Identity:
        model_id = "intfloat/e5-large"

    class _Client:
        identity = _Identity()

        def embed_documents(self, texts):
            inference_started.set()
            assert allow_inference.wait(timeout=3)
            return [[0.0] * 1024 for _ in texts]

    monkeypatch.setattr(
        "airunner_services.workers.llm_generate_worker.verified_e5_client_for_manager",
        lambda _manager: _Client(),
    )
    request_id, future = worker.submit_embedding_documents(["active passage"])
    message = worker.get_item_from_queue()
    inference = threading.Thread(
        target=worker._handle_embedding_message, args=(message,)
    )
    inference.start()
    assert inference_started.wait(timeout=2)

    worker.stop()
    assert future.running()
    assert worker._embedding_requests[request_id]["cancel_event"].is_set()
    allow_inference.set()
    inference.join(timeout=2)

    assert not inference.is_alive()
    assert future.done()
    with pytest.raises(EmbeddingWorkerUnavailableError, match="cancelled"):
        future.result()
    assert request_id not in worker._embedding_requests


@pytest.mark.parametrize("texts", [[], ["   "], ["x" * 8193], [None]])
def test_worker_rejects_invalid_embedding_payloads(texts) -> None:
    worker = LLMGenerateWorker()
    worker.running = True
    with pytest.raises(ValueError):
        worker.submit_embedding_documents(texts)
    worker.stop()
