"""Compatibility tests for the legacy WhisperModelManager wrapper."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner.components.stt.managers.whisper_model_manager import (
    WhisperModelManager,
)


def test_process_audio_emits_transcription_when_text_is_returned():
    api = SimpleNamespace(
        stt=SimpleNamespace(audio_processor_response=MagicMock())
    )
    manager = SimpleNamespace(
        transcribe=MagicMock(return_value="transcribed text"),
        api=api,
    )

    WhisperModelManager.process_audio(manager, {"item": b"\x00\x00"})

    manager.transcribe.assert_called_once_with({"item": b"\x00\x00"})
    api.stt.audio_processor_response.assert_called_once_with(
        "transcribed text"
    )


def test_process_audio_skips_empty_transcription():
    api = SimpleNamespace(
        stt=SimpleNamespace(audio_processor_response=MagicMock())
    )
    manager = SimpleNamespace(
        transcribe=MagicMock(return_value=""),
        api=api,
    )

    WhisperModelManager.process_audio(manager, {"item": b"\x00\x00"})

    api.stt.audio_processor_response.assert_not_called()