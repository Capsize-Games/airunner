"""Regression tests for TTS vocalizer API resolution."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np

from airunner.enums import TTSModel
from airunner.components.tts.workers import tts_vocalizer_worker
from airunner.components.tts.workers.tts_vocalizer_worker import (
    TTSVocalizerWorker,
)


def _patch_vocalizer_settings(monkeypatch) -> None:
    """Patch settings properties with lightweight test doubles."""
    monkeypatch.setattr(
        TTSVocalizerWorker,
        "chatbot_voice_model_type",
        property(lambda self: TTSModel.OPENVOICE),
    )
    monkeypatch.setattr(
        TTSVocalizerWorker,
        "sound_settings",
        property(lambda self: SimpleNamespace(playback_device="pulse")),
    )


def test_start_stream_refreshes_sounddevice_manager(monkeypatch):
    """Playback should recover when the cached API reference is stale."""
    _patch_vocalizer_settings(monkeypatch)
    manager = SimpleNamespace(out_stream=None)

    def initialize_output_stream(**_kwargs):
        manager.out_stream = object()
        return True

    manager.initialize_output_stream = MagicMock(
        side_effect=initialize_output_stream
    )
    manager._stop_output_stream = MagicMock()

    monkeypatch.setattr(
        tts_vocalizer_worker,
        "sd",
        SimpleNamespace(
            query_devices=lambda *_args, **_kwargs: {
                "default_samplerate": 48000
            },
            PortAudioError=RuntimeError,
            PaErrorCode=SimpleNamespace(INVALID_SAMPLE_RATE=-1),
        ),
    )

    worker = TTSVocalizerWorker.__new__(TTSVocalizerWorker)
    worker.logger = MagicMock()
    worker.api = SimpleNamespace()
    worker._model_samplerate = None
    worker._stream_samplerate = None
    worker._device_default_samplerate = None
    worker.refresh_api_reference = MagicMock(
        return_value=SimpleNamespace(sounddevice_manager=manager)
    )

    TTSVocalizerWorker.start_stream(worker)

    manager.initialize_output_stream.assert_called_once_with(
        samplerate=24000,
        channels=1,
        device_name="pulse",
    )
    assert worker._stream_samplerate == 24000


def test_is_espeak_uses_enum_model_type(monkeypatch):
    """Espeak detection should match the enum returned by settings."""
    monkeypatch.setattr(
        TTSVocalizerWorker,
        "chatbot_voice_model_type",
        property(lambda self: TTSModel.ESPEAK),
    )
    worker = TTSVocalizerWorker.__new__(TTSVocalizerWorker)

    assert TTSVocalizerWorker.is_espeak.__get__(worker) is True


def test_handle_message_refreshes_sounddevice_manager(monkeypatch):
    """Playback should write audio after refreshing a stale API."""
    monkeypatch.setattr(tts_vocalizer_worker.QThread, "msleep", lambda *_: None)
    manager = SimpleNamespace(
        out_stream=object(),
        write_to_output=MagicMock(return_value=True),
    )
    worker = TTSVocalizerWorker.__new__(TTSVocalizerWorker)
    worker.logger = MagicMock()
    worker.api = SimpleNamespace()
    worker.accept_message = True
    worker.started = False
    worker._model_samplerate = None
    worker._stream_samplerate = None
    worker.refresh_api_reference = MagicMock(
        return_value=SimpleNamespace(sounddevice_manager=manager)
    )

    TTSVocalizerWorker.handle_message(
        worker,
        np.array([0.1, 0.2, 0.3], dtype=np.float32),
    )

    manager.write_to_output.assert_called_once()
    assert worker.started is True


def test_sounddevice_manager_uses_local_fallback_when_shared_manager_missing(
    monkeypatch,
):
    """Playback should create one local manager when the shared API lacks one."""
    manager = SimpleNamespace()
    monkeypatch.setattr(
        tts_vocalizer_worker,
        "SoundDeviceManager",
        lambda: manager,
    )

    worker = TTSVocalizerWorker.__new__(TTSVocalizerWorker)
    worker.logger = MagicMock()
    worker.api = SimpleNamespace()
    worker.refresh_api_reference = MagicMock(return_value=SimpleNamespace())

    first_manager = TTSVocalizerWorker._sounddevice_manager(worker)
    second_manager = TTSVocalizerWorker._sounddevice_manager(worker)

    assert first_manager is manager
    assert second_manager is manager
    worker.logger.warning.assert_called_once_with(
        "Falling back to a worker-local SoundDeviceManager for TTS playback"
    )