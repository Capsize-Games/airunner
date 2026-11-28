"""Unit tests for the local-fallback STT extraction helpers.

_validate_audio_payload and _await_transcription were extracted to
keep _transcribe within the long-function threshold. These tests pin
the decode/size checks and the emit/wait failure mappings.
"""

import base64
from queue import Queue
from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.runtimes.local_fallback_stt_client import (
    LocalFallbackSTTClient,
    MAX_LOCAL_FALLBACK_AUDIO_BYTES,
)


def _client():
    client = LocalFallbackSTTClient.__new__(LocalFallbackSTTClient)
    client._failure_response = MagicMock(return_value="failure")
    client._timeout_seconds = 0.01
    client._mediator = MagicMock()
    client._signal_lock = MagicMock()
    client._signal_lock.__enter__ = MagicMock(return_value=None)
    client._signal_lock.__exit__ = MagicMock(return_value=False)
    client._emit_signal = MagicMock()
    return client


def test_validate_audio_ok():
    client = _client()
    invocation = SimpleNamespace(
        audio_b64=base64.b64encode(b"abc").decode()
    )
    audio, failure = client._validate_audio_payload("r1", invocation)
    assert audio == b"abc"
    assert failure is None


def test_validate_audio_rejects_bad_base64():
    client = _client()
    invocation = SimpleNamespace(audio_b64="!!!not-base64!!!")
    audio, failure = client._validate_audio_payload("r1", invocation)
    assert audio is None
    assert failure == "failure"
    client._failure_response.assert_called_once_with(
        "r1", "stt_invalid_audio", "Invalid base64 audio payload"
    )


def test_validate_audio_rejects_oversize():
    client = _client()
    big = base64.b64encode(b"x" * (MAX_LOCAL_FALLBACK_AUDIO_BYTES + 1)).decode()
    invocation = SimpleNamespace(audio_b64=big)
    audio, failure = client._validate_audio_payload("r1", invocation)
    assert audio is None
    assert failure == "failure"
    assert client._failure_response.call_args[0][1] == "stt_invalid_audio"


def test_await_timeout_returns_failure():
    client = _client()
    req = SimpleNamespace(request_id="r1")
    transcription, failure = client._await_transcription(req, b"abc")
    assert transcription is None
    assert failure == "failure"
    assert client._failure_response.call_args[0][1] == "stt_timeout"
    client._mediator.unregister.assert_called_once()


def test_await_emit_error_returns_failure():
    client = _client()
    client._emit_signal.side_effect = RuntimeError("no backend")
    req = SimpleNamespace(request_id="r1")
    transcription, failure = client._await_transcription(req, b"abc")
    assert transcription is None
    assert failure == "failure"
    assert client._failure_response.call_args[0][1] == "stt_invoke_failed"
    client._mediator.unregister.assert_called_once()


def test_await_success_returns_transcription():
    client = _client()

    def _fake_queue_get(timeout):
        client._mediator.register.call_args[0][1](
            {"request_id": "r1", "transcription": "hello"}
        )
        return "x"

    original_queue = Queue
    import airunner_services.runtimes.local_fallback_stt_client as mod

    class _FakeQueue(Queue):
        def get(self, timeout=None):
            _fake_queue_get(timeout)
            return "hello"

    try:
        mod.Queue = _FakeQueue
        req = SimpleNamespace(request_id="r1")
        transcription, failure = client._await_transcription(req, b"abc")
    finally:
        mod.Queue = original_queue
    assert transcription == "hello"
    assert failure is None
    client._emit_signal.assert_called_once()
