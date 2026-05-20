"""Tests for LLMGenerateWorker pending-request retry behavior."""

import threading
from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.workers.llm_generate_worker import (
    LLMGenerateWorker,
)


def _build_worker(handle_request_result):
    worker = LLMGenerateWorker.__new__(LLMGenerateWorker)
    worker.logger = Mock()
    worker.context_manager = SimpleNamespace(all_contexts=lambda: {})
    worker._model_manager_lock = threading.Lock()
    worker._model_manager = SimpleNamespace(handle_request=Mock(return_value=handle_request_result))
    worker._interrupted = False
    worker._pending_llm_request = None
    worker._pending_unload_request = None
    worker._load_documents_into_rag = Mock()
    worker.emit_signal = Mock()
    return worker


def _message():
    return {
        "request_id": "req-1",
        "request_data": {
            "llm_request": SimpleNamespace(rag_files=None),
            "prompt": "Hello",
        },
    }


def test_clears_pending_request_for_non_retryable_error():
    worker = _build_worker(
        {
            "response": "Error: unsupported architecture",
            "error": "unsupported architecture",
        }
    )

    message = _message()
    LLMGenerateWorker.handle_message(worker, message)

    assert worker._pending_llm_request is None


def test_keeps_pending_request_only_for_download_retry_error():
    worker = _build_worker(
        {
            "response": "Error: model is not ready yet (download in progress).",
            "retry_after_download": True,
        }
    )

    message = _message()
    LLMGenerateWorker.handle_message(worker, message)

    assert worker._pending_llm_request == message


def test_embedding_download_complete_retries_pending_request():
    worker = _build_worker({"response": "ok"})
    pending_request = _message()
    worker._pending_llm_request = pending_request
    worker._download_dialog_showing = True
    worker._download_dialog = object()
    worker.handle_message = Mock()
    worker._retry_pending_document_index_requests = Mock()

    LLMGenerateWorker.on_huggingface_download_complete_signal(
        worker,
        {
            "repo_id": "intfloat/e5-large",
            "model_path": "/tmp/embedding",
            "model_type": "embedding",
        },
    )

    worker._retry_pending_document_index_requests.assert_called_once_with()
    worker.handle_message.assert_called_once_with(pending_request)
    assert worker._pending_llm_request is None


def test_embedding_download_request_is_not_ignored(monkeypatch):
    worker = _build_worker({"response": "ok"})
    worker._download_dialog_showing = False
    worker._get_model_info = Mock(
        return_value={
            "name": "intfloat/e5-large",
            "repo_id": "intfloat/e5-large",
            "model_type": "llm",
            "setup_quantization": False,
            "quantization_bits": 4,
        }
    )
    worker._is_headless_mode = Mock(return_value=True)
    worker._download_headless = Mock(return_value=True)
    worker._show_download_dialog = Mock()

    LLMGenerateWorker.on_llm_model_download_required_signal(
        worker,
        {
            "repo_id": "intfloat/e5-large",
            "model_type": "embedding",
            "model_path": "/tmp/models/intfloat/e5-large",
            "missing_files": ["config.json"],
        },
    )

    worker._download_headless.assert_called_once()


def test_request_unload_after_interrupt_queues_immediately_when_idle():
    worker = _build_worker({"response": "ok"})
    worker.add_to_queue = Mock()
    worker.llm_on_interrupt_process_signal = Mock()

    result = LLMGenerateWorker.request_unload_after_interrupt(
        worker,
        {"source": "ui"},
    )

    assert result is True
    worker.llm_on_interrupt_process_signal.assert_called_once_with(
        {"source": "ui"}
    )
    worker.add_to_queue.assert_called_once_with(
        {"_message_type": "llm_unload", "data": {"source": "ui"}}
    )
    assert worker._pending_unload_request is None


def test_handle_message_flushes_pending_unload_request_after_completion():
    worker = _build_worker({"response": "done"})
    worker.add_to_queue = Mock()
    worker._pending_unload_request = {"source": "ui"}

    LLMGenerateWorker.handle_message(worker, _message())

    worker.add_to_queue.assert_called_once_with(
        {"_message_type": "llm_unload", "data": {"source": "ui"}}
    )
    assert worker._pending_unload_request is None