"""Tests for OpenVoice settings changes in the TTS generator worker."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.tts.workers.tts_generator_worker import (
    TTSGeneratorWorker,
)


def test_reference_speaker_change_reloads_local_embeddings():
    tts = SimpleNamespace(reload_speaker_embeddings=Mock())
    worker = SimpleNamespace(
        tts=tts,
        _daemon_client=lambda: None,
    )

    TTSGeneratorWorker.on_application_settings_changed_signal(
        worker,
        {
            "setting_name": "openvoice_settings",
            "column_name": "reference_speaker_path",
            "val": "/tmp/voice.wav",
        },
    )

    tts.reload_speaker_embeddings.assert_called_once_with(
        reference_speaker_path="/tmp/voice.wav"
    )