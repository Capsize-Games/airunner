"""Regression tests for STT audio capture API resolution."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner.components.stt.workers.audio_capture_worker import (
    AudioCaptureWorker,
)


def _patch_worker_settings(monkeypatch) -> None:
    """Patch settings properties with lightweight test doubles."""
    monkeypatch.setattr(
        AudioCaptureWorker,
        "stt_settings",
        property(lambda self: SimpleNamespace(channels=1)),
    )
    monkeypatch.setattr(
        AudioCaptureWorker,
        "sound_settings",
        property(
            lambda self: SimpleNamespace(
                recording_device="pulse",
                playback_device="",
            )
        ),
    )


def test_start_listening_refreshes_sounddevice_manager(monkeypatch):
    """Capture should recover when the cached API reference is stale."""
    _patch_worker_settings(monkeypatch)
    manager = SimpleNamespace(in_stream=None, out_stream=None)

    def initialize_input_stream(**_kwargs):
        manager.in_stream = SimpleNamespace(samplerate=16000)
        return True

    manager.initialize_input_stream = MagicMock(
        side_effect=initialize_input_stream
    )
    manager.initialize_output_stream = MagicMock(return_value=True)
    manager._stop_input_stream = MagicMock()

    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        SimpleNamespace(
            query_devices=lambda: [
                {"name": "pulse", "max_input_channels": 1}
            ]
        ),
    )

    worker = AudioCaptureWorker.__new__(AudioCaptureWorker)
    worker.logger = MagicMock()
    worker.api = SimpleNamespace()
    worker.listening = False
    worker._use_playback_stream = False
    worker.refresh_api_reference = MagicMock(
        return_value=SimpleNamespace(sounddevice_manager=manager)
    )

    AudioCaptureWorker._start_listening(worker)

    assert worker.listening is True
    manager.initialize_input_stream.assert_called_once()


def test_start_listening_stays_disabled_without_sounddevice_manager(
    monkeypatch,
):
    """Capture should not enter listening mode without one audio manager."""
    _patch_worker_settings(monkeypatch)
    worker = AudioCaptureWorker.__new__(AudioCaptureWorker)
    worker.logger = MagicMock()
    worker.api = SimpleNamespace()
    worker.listening = False
    worker._use_playback_stream = False
    worker.refresh_api_reference = MagicMock(return_value=SimpleNamespace())

    AudioCaptureWorker._start_listening(worker)

    assert worker.listening is False
    worker.logger.error.assert_called_once_with(
        "Audio capture API is missing sounddevice_manager"
    )