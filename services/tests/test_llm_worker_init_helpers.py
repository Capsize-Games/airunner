"""Unit tests for the LLMGenerateWorker __init__ helper split.

The constructor was decomposed into _build_signal_handlers,
_initialize_worker_state, and _initialize_lifecycle_state to keep
__init__ within the long-function threshold. These tests assert every
signal mapping and attribute default is preserved.
"""

import threading

from airunner_services.workers.llm_generate_worker import (
    LLMGenerateWorker,
    SignalCode,
)


def _make_obj():
    return LLMGenerateWorker.__new__(LLMGenerateWorker)


def test_signal_handlers_map_all_codes():
    obj = _make_obj()
    obj._initialize_worker_state = LLMGenerateWorker._initialize_worker_state.__get__(obj)
    handlers = obj._build_signal_handlers()
    assert set(handlers) == {
        SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
        SignalCode.LLM_CLEAR_HISTORY_SIGNAL,
        SignalCode.RAG_INDEX_ALL_DOCUMENTS,
        SignalCode.RAG_INDEX_SELECTED_DOCUMENTS,
        SignalCode.RAG_INDEXING_PROGRESS,
        SignalCode.RAG_INDEXING_COMPLETE,
        SignalCode.RAG_INDEX_CANCEL,
        SignalCode.RAG_DELETE_DOCUMENT,
        SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
    }
    assert callable(handlers[SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL])


def test_worker_state_defaults():
    obj = _make_obj()
    obj._initialize_worker_state()
    assert obj._model_manager is None
    assert isinstance(obj._model_manager_lock, type(threading.Lock()))
    assert obj._interrupted is False
    assert obj._download_dialog_showing is False
    assert obj._download_dialog is None
    assert obj._pending_llm_request is None
    assert obj._pending_llm_requests == {}
    assert obj._retry_waiting_request_ids == set()
    assert obj._retry_waiting_order == []
    assert obj._retry_enqueued_epoch == {}
    assert obj._download_epoch == 0
    assert isinstance(obj._active_request_lock, type(threading.RLock()))
    assert obj._active_llm_request_id is None
    assert obj._cancelled_request_ids == set()
    assert obj._embedding_requests == {}
    assert obj._accept_embedding_requests is True
    assert obj._pending_unload_request is None
    assert obj.manager_thread is None
    assert obj.download_manager is None


def test_lifecycle_state_defaults(monkeypatch):
    monkeypatch.delenv("AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("AIRUNNER_LLM_AUTO_UNLOAD", raising=False)
    obj = _make_obj()
    obj._initialize_lifecycle_state()
    assert obj._last_request_time is None
    assert obj._inactivity_timer is None
    assert obj._inactivity_timeout == 300
    assert obj._auto_unload_enabled is False


def test_lifecycle_state_reads_env_overrides(monkeypatch):
    monkeypatch.setenv("AIRUNNER_LLM_INACTIVITY_TIMEOUT_SECONDS", "600")
    monkeypatch.setenv("AIRUNNER_LLM_AUTO_UNLOAD", "1")
    obj = _make_obj()
    obj._initialize_lifecycle_state()
    assert obj._inactivity_timeout == 600
    assert obj._auto_unload_enabled is True
