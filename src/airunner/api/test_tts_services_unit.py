"""
Unit tests for TTSAPIService in airunner.api.tts_services.
Covers all public methods and signal emission logic.
"""

import pytest
from unittest.mock import MagicMock
from airunner.api.tts_services import TTSAPIService
from airunner.enums import SignalCode


@pytest.fixture
def mock_emit_signal():
    return MagicMock()


@pytest.fixture
def tts_service(mock_emit_signal):
    return TTSAPIService(emit_signal=mock_emit_signal)


def test_play_audio_emits_signal(tts_service, mock_emit_signal):
    tts_service.play_audio("hello")
    mock_emit_signal.assert_called_once_with(
        SignalCode.TTS_QUEUE_SIGNAL,
        {"message": "hello", "is_end_of_message": True},
    )


def test_toggle_emits_signal(tts_service, mock_emit_signal):
    tts_service.toggle(True)
    mock_emit_signal.assert_called_once_with(
        SignalCode.TOGGLE_TTS_SIGNAL, {"enabled": True}
    )


def test_start_emits_signal(tts_service, mock_emit_signal):
    tts_service.start()
    mock_emit_signal.assert_called_once_with(SignalCode.TTS_ENABLE_SIGNAL, {})


def test_stop_emits_signal(tts_service, mock_emit_signal):
    tts_service.stop()
    mock_emit_signal.assert_called_once_with(SignalCode.TTS_DISABLE_SIGNAL, {})


def test_add_to_stream_emits_signal(tts_service, mock_emit_signal):
    tts_service.add_to_stream("foo")
    mock_emit_signal.assert_called_once_with(
        SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
        {"message": "foo"},
    )


def test_disable_emits_signal(tts_service, mock_emit_signal):
    tts_service.disable()
    mock_emit_signal.assert_called_once_with(SignalCode.TTS_DISABLE_SIGNAL, {})
