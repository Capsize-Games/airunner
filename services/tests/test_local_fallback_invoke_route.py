"""Unit tests for the LocalFallbackTTSClient invoke routing helpers.

The routing was extracted to keep invoke() within the long-function
threshold. These tests pin the action dispatch and backend-selection
branches with mocks so refactors cannot silently reroute a request.
"""

from unittest.mock import MagicMock

import pytest

from airunner_services.runtimes.contracts import (
    RuntimeAction,
    RuntimeKind,
)
from airunner_services.runtimes.local_fallback import (
    LocalFallbackTTSClient,
)


def _make_client():
    client = LocalFallbackTTSClient.__new__(LocalFallbackTTSClient)
    client._status_response = MagicMock(return_value="status")
    client._load_model = MagicMock(return_value="loaded")
    client._unload_model = MagicMock(return_value="unloaded")
    client._failure_response = MagicMock(return_value="failure")
    client._invoke_headless_runtime = MagicMock(return_value="headless")
    client._invoke_playback_runtime = MagicMock(return_value="playback")
    client._headless_tts_worker = MagicMock(return_value=None)
    client._is_espeak_model_type = MagicMock(return_value=False)
    client._allow_legacy_playback = False
    return client


def _request(action, payload=None, metadata=None):
    req = MagicMock()
    req.runtime = RuntimeKind.TTS
    req.action = action
    req.request_id = "req-1"
    req.payload = payload or {}
    req.metadata = metadata
    return req


def test_route_status():
    client = _make_client()
    assert client._route_action(_request(RuntimeAction.STATUS)) == "status"


def test_route_load_model():
    client = _make_client()
    req = _request(RuntimeAction.LOAD_MODEL, metadata={"model_type": "x"})
    assert client._route_action(req) == "loaded"
    client._load_model.assert_called_once_with("req-1", "x")


def test_route_unload_model():
    client = _make_client()
    assert client._route_action(_request(RuntimeAction.UNLOAD_MODEL)) == "unloaded"


def test_route_invoke_returns_none():
    client = _make_client()
    assert client._route_action(_request(RuntimeAction.INVOKE)) is None


def test_route_rejects_unknown_action():
    client = _make_client()
    with pytest.raises(ValueError, match="only supports invoke"):
        client._route_action(_request(MagicMock()))


def test_espeak_route_skips_worker_selection():
    client = _make_client()
    client._is_espeak_model_type.return_value = True
    worker, failure = client._select_tts_worker_or_failure("r", "espeak", None)
    assert (worker, failure) == (None, None)
    client._headless_tts_worker.assert_not_called()


def test_worker_route_returns_worker():
    client = _make_client()
    worker = MagicMock()
    client._headless_tts_worker.return_value = worker
    got, failure = client._select_tts_worker_or_failure("r", "other", None)
    assert got is worker and failure is None


def test_deferred_active_model_fails():
    client = _make_client()
    worker = MagicMock()
    worker._active_tts_model.return_value = "openvoice"  # deferred type
    client._headless_tts_worker.return_value = worker
    got, failure = client._select_tts_worker_or_failure("r", "other", None)
    assert failure == "failure"
    client._failure_response.assert_called_once()


def test_invoke_rejects_non_tts_runtime():
    client = _make_client()
    req = _request(RuntimeAction.INVOKE)
    req.runtime = MagicMock()  # not RuntimeKind.TTS
    with pytest.raises(ValueError, match="only supports TTS"):
        client.invoke(req)


def test_invocation_routes_to_playback_when_allowed():
    client = _make_client()
    client._allow_legacy_playback = True
    req = _request(RuntimeAction.INVOKE)
    invocation = MagicMock()
    invocation.metadata = {}
    assert client._invoke_tts_route(req, invocation) == "playback"


def test_invocation_fails_without_backend():
    client = _make_client()
    req = _request(RuntimeAction.INVOKE)
    invocation = MagicMock()
    invocation.metadata = {}
    assert client._invoke_tts_route(req, invocation) == "failure"
    assert client._failure_response.call_args[0][0] == "req-1"
    assert (
        client._failure_response.call_args[0][2]
        == "No headless TTS backend is configured"
    )
