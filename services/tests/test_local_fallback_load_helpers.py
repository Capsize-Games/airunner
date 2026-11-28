"""Unit tests for the local TTS load-model extraction helpers.

_load_model_on_worker and _wait_for_tts_load were extracted to keep
_load_model within the long-function threshold. These tests pin the
deferred-type gate, the load/status wiring, and the wait fallback.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_common.contract_enums import ModelStatus
from airunner_services.ipc.messages import EnvelopeStatus

from airunner_services.runtimes.local_fallback import (
    LocalFallbackTTSClient,
)


def _make_client():
    client = LocalFallbackTTSClient.__new__(LocalFallbackTTSClient)
    client._failure_response = MagicMock(return_value="failure")
    client._cache_status = MagicMock()
    client._status_metadata = MagicMock(return_value={})
    client._wait_for_model_status = MagicMock(return_value="waited")
    return client


def _worker(status):
    worker = MagicMock()
    worker._active_tts_model = MagicMock(return_value=None)
    worker._load_tts = MagicMock()
    worker._current_tts_status = MagicMock(return_value=status)
    return worker


def test_worker_loaded_returns_success_envelope():
    client = _make_client()
    worker = _worker(ModelStatus.LOADED)
    out = client._load_model_on_worker("r1", worker)
    worker._load_tts.assert_called_once()
    assert out.status is EnvelopeStatus.SUCCEEDED
    assert out.payload["model_status"]


def test_worker_ready_also_succeeds():
    client = _make_client()
    worker = _worker(ModelStatus.READY)
    out = client._load_model_on_worker("r1", worker)
    assert out.status is EnvelopeStatus.SUCCEEDED


def test_worker_failed_returns_load_failure():
    client = _make_client()
    worker = _worker(ModelStatus.FAILED)
    out = client._load_model_on_worker("r1", worker)
    assert out == "failure"
    client._failure_response.assert_called_once_with(
        "r1", "tts_load_failed", "TTS load failed"
    )


def test_worker_unusable_returns_failure():
    client = _make_client()
    worker = MagicMock()
    del worker._load_tts
    del worker._current_tts_status
    out = client._load_model_on_worker("r1", worker)
    assert out == "failure"
    client._failure_response.assert_called_once_with(
        "r1", "tts_load_failed", "Headless TTS worker is unavailable"
    )


def test_worker_non_terminal_returns_retryable_failure():
    client = _make_client()
    worker = _worker(ModelStatus.LOADING)
    out = client._load_model_on_worker("r1", worker)
    assert out == "failure"
    assert client._failure_response.call_args[1].get("retryable") is True


def test_wait_for_load_delegates_to_signal_wait():
    client = _make_client()
    out = client._wait_for_tts_load("r1")
    assert out == "waited"
    client._wait_for_model_status.assert_called_once()
