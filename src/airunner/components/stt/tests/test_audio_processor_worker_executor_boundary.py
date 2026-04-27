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
    )

    AudioProcessorWorker.handle_message(worker, {"item": b"\x00\x00"})

    executor.transcribe.assert_not_called()
    api.stt.audio_processor_response.assert_not_called()


def test_stt_load_forwards_to_executor_and_starts_capture():
    executor = SimpleNamespace(load=MagicMock())
    worker = SimpleNamespace(
        _executor=executor,
        emit_signal=MagicMock(),
    )

    AudioProcessorWorker._stt_load(worker)

    executor.load.assert_called_once_with()
    worker.emit_signal.assert_called_once()