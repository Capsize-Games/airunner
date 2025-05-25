import pytest
from unittest.mock import MagicMock
from airunner.api.stt_services import STTAPIService
from airunner.enums import SignalCode


@pytest.fixture
def stt_service():
    mock_emit_signal = MagicMock()
    service = STTAPIService(emit_signal=mock_emit_signal)
    return service


def test_audio_processor_response_happy(stt_service):
    transcription = "Hello, this is a test transcription"
    stt_service.audio_processor_response(transcription)
    stt_service.emit_signal.assert_called_once_with(
        SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
        {"transcription": transcription},
    )


def test_audio_processor_response_empty_string(stt_service):
    # Test with empty string
    transcription = ""
    stt_service.audio_processor_response(transcription)
    stt_service.emit_signal.assert_called_once_with(
        SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
        {"transcription": transcription},
    )


def test_audio_processor_response_bad_path(stt_service):
    # Bad path: Test with None transcription (no validation in method, so just verify it passes through)
    transcription = None
    stt_service.audio_processor_response(transcription)
    stt_service.emit_signal.assert_called_once_with(
        SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
        {"transcription": transcription},
    )


def test_audio_processor_response_complex_data(stt_service):
    # Test with complex transcription data
    transcription = {
        "text": "Hello world",
        "confidence": 0.95,
        "timestamps": [(0.0, 1.0), (1.0, 2.0)],
    }
    stt_service.audio_processor_response(transcription)
    stt_service.emit_signal.assert_called_once_with(
        SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
        {"transcription": transcription},
    )
