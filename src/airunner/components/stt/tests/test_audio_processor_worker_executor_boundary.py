"""Safe tests for the STT processor worker executor boundary."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner.components.stt.workers.audio_processor_worker import (
    AudioProcessorWorker,
)


def test_handle_message_uses_executor_for_transcription():
    executor = SimpleNamespace(
        stt_is_loaded=True,
        transcribe=MagicMock(return_value="hello world"),
    )
    api = SimpleNamespace(
        stt=SimpleNamespace(audio_processor_response=MagicMock())
    )
    worker = SimpleNamespace(
        _executor=executor,
        logger=MagicMock(),
        api=api,
        _daemon_client=lambda: None,
    )
    message = {"item": b"\x01\x00\x02\x00"}

    AudioProcessorWorker.handle_message(worker, message)

    executor.transcribe.assert_called_once_with(message)
    api.stt.audio_processor_response.assert_called_once_with("hello world")


def test_handle_message_skips_when_executor_is_unloaded():
    executor = SimpleNamespace(
        stt_is_loaded=False,
        transcribe=MagicMock(),
    )
    api = SimpleNamespace(
        stt=SimpleNamespace(audio_processor_response=MagicMock())
    )
    worker = SimpleNamespace(
        _executor=executor,
        logger=MagicMock(),
        api=api,
        _daemon_client=lambda: None,
    )

    AudioProcessorWorker.handle_message(worker, {"item": b"\x00\x00"})

    executor.transcribe.assert_not_called()
    api.stt.audio_processor_response.assert_not_called()


def test_stt_load_forwards_to_executor_and_starts_capture():
    executor = SimpleNamespace(load=MagicMock())
    worker = SimpleNamespace(
        _executor=executor,
        emit_signal=MagicMock(),
        _daemon_client=lambda: None,
    )

    AudioProcessorWorker._stt_load(worker)

    executor.load.assert_called_once_with()
    worker.emit_signal.assert_called_once()


def test_handle_message_prefers_daemon_transcription():
    daemon_client = SimpleNamespace(
        transcribe_audio=MagicMock(return_value={"text": "daemon result"})
    )
    executor = SimpleNamespace(
        stt_is_loaded=True,
        transcribe=MagicMock(return_value="local result"),
    )
    api = SimpleNamespace(
        daemon_client=daemon_client,
        headless=False,
        stt=SimpleNamespace(audio_processor_response=MagicMock()),
    )
    worker = AudioProcessorWorker.__new__(AudioProcessorWorker)
    worker._executor = executor
    worker.logger = MagicMock()
    worker.api = api

    AudioProcessorWorker.handle_message(worker, {"item": b"\x01\x00"})

    daemon_client.transcribe_audio.assert_called_once_with(
        b"\x01\x00",
        mime_type="application/octet-stream",
    )
    executor.transcribe.assert_not_called()
    api.stt.audio_processor_response.assert_called_once_with("daemon result")


def test_stt_load_skips_local_executor_when_daemon_backed():
    executor = SimpleNamespace(load=MagicMock())
    worker = AudioProcessorWorker.__new__(AudioProcessorWorker)
    worker._executor = executor
    worker.logger = MagicMock()
    worker.emit_signal = MagicMock()
    worker.api = SimpleNamespace(
        daemon_client=SimpleNamespace(),
        headless=False,
    )

    AudioProcessorWorker._stt_load(worker)

    executor.load.assert_not_called()
    worker.emit_signal.assert_not_called()