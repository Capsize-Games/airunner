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