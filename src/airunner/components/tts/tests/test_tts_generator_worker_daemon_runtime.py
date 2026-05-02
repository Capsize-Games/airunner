"""Tests for daemon-backed TTS generator worker behavior."""

import queue
from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.tts.workers.tts_generator_worker import (
    TTSGeneratorWorker,
)
from airunner.components.tts.workers.tts_vocalizer_worker import (
    TTSVocalizerWorker,
)


class FakeDaemonClient:
    """Minimal daemon client double for TTS worker tests."""

    def __init__(self):
        self.calls = []

    def synthesize_tts(self, text, **kwargs):
        self.calls.append(("synthesize", text, kwargs))
        return b"wav-bytes"

    def cancel_runtime(self, runtime_name, **kwargs):
        self.calls.append(("cancel", runtime_name, kwargs))
        return {"status": "cancelled"}


def test_generate_via_daemon_uses_tts_route_and_clears_request_id():
    client = FakeDaemonClient()
    worker = SimpleNamespace(
        _active_request_id=None,
        chatbot_voice_settings=SimpleNamespace(voice="alloy"),
        path_settings=SimpleNamespace(tts_model_path="/tmp/tts-model"),
        logger=SimpleNamespace(error=lambda *args, **kwargs: None),
        _daemon_client=lambda: client,
        _decode_daemon_audio=lambda audio_bytes: ("decoded", audio_bytes),
    )

    response = TTSGeneratorWorker._generate_via_daemon(
        worker,
        "Speak this",
        "openvoice",
    )

    assert response == ("decoded", b"wav-bytes")
    assert client.calls[0][0] == "synthesize"
    assert client.calls[0][2]["request_id"]
    assert worker._active_request_id is None


def test_interrupt_process_cancels_active_daemon_request():
    client = FakeDaemonClient()
    worker = SimpleNamespace(
        _active_request_id="tts-req-1",
        play_queue=[],
        play_queue_started=False,
        tokens=[],
        _sentence_buffer=[],
        queue=queue.Queue(),
        do_interrupt=False,
        paused=False,
        tts=None,
        _daemon_client=lambda: client,
    )

    TTSGeneratorWorker.on_interrupt_process_signal(worker)

    assert client.calls[0][0] == "cancel"
    assert client.calls[0][1] == "tts"
    assert worker.do_interrupt is True


def test_handle_message_dispatches_interrupt_requests():
    worker = SimpleNamespace(on_interrupt_process_signal=Mock())

    TTSGeneratorWorker.handle_message(
        worker,
        {"_message_type": "interrupt", "data": {"source": "test"}},
    )

    worker.on_interrupt_process_signal.assert_called_once_with(
        {"source": "test"}
    )


def test_vocalizer_handle_message_dispatches_interrupt_requests():
    worker = SimpleNamespace(on_interrupt_process_signal=Mock())

    TTSVocalizerWorker.handle_message(
        worker,
        {"_message_type": "interrupt", "data": {"source": "test"}},
    )

    worker.on_interrupt_process_signal.assert_called_once_with(
        {"source": "test"}
    )