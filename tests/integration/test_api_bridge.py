"""Integration tests for the APIBridge and SignalAPIAdapter.

Verifies that the bridge correctly translates GUI signals to API calls
and that the adapter's handler map covers all expected signal codes.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from airunner.api.api_bridge import APIBridge, APIBridgeError
from airunner.api.signal_api_adapter import SignalAPIAdapter
from airunner.enums import SignalCode


class TestAPIBridge:
    """Verify APIBridge wraps GuiDaemonClient correctly."""

    @pytest.fixture
    def mock_daemon_client(self) -> MagicMock:
        """Return a mocked GuiDaemonClient."""
        client = MagicMock()
        client.is_available.return_value = True
        client.start_art_generation.return_value = {"job_id": "test-job-1"}
        client.wait_art_job.return_value = b"fake-png-bytes"
        client.synthesize_tts.return_value = b"fake-audio-bytes"
        client.transcribe_audio.return_value = {"text": "hello"}
        client.load_runtime.return_value = {"status": "loaded"}
        client.unload_runtime.return_value = {"status": "unloaded"}
        client.runtime_status.return_value = {"status": "loaded"}
        return client

    @pytest.fixture
    def bridge(self, mock_daemon_client) -> APIBridge:
        """Return an APIBridge with a mocked daemon client."""
        return APIBridge(mock_daemon_client)

    def test_is_connected(self, bridge, mock_daemon_client):
        """is_connected delegates to the daemon client."""
        assert bridge.is_connected is True
        mock_daemon_client.is_available.assert_called_once()

    def test_ensure_connected(self, bridge, mock_daemon_client):
        """ensure_connected delegates to the daemon client."""
        mock_daemon_client.ensure_connected.return_value = True
        assert bridge.ensure_connected() is True
        mock_daemon_client.ensure_connected.assert_called_once_with(
            auto_start=True
        )

    def test_generate_image_submits_job(self, bridge, mock_daemon_client):
        """generate_image submits to the daemon and returns a job_id."""
        response = bridge.generate_image(prompt="a cat")
        assert response["job_id"] == "test-job-1"
        mock_daemon_client.start_art_generation.assert_called_once()

    def test_cancel_generation(self, bridge, mock_daemon_client):
        """cancel_generation forwards to the daemon client."""
        bridge.cancel_generation("test-job-1")
        mock_daemon_client.cancel_art_job.assert_called_once_with("test-job-1")

    def test_synthesize_tts(self, bridge, mock_daemon_client):
        """synthesize_tts returns audio bytes."""
        result = bridge.synthesize_tts("hello world")
        assert result == b"fake-audio-bytes"
        mock_daemon_client.synthesize_tts.assert_called_once()

    def test_transcribe_audio(self, bridge, mock_daemon_client):
        """transcribe_audio returns transcription dict."""
        result = bridge.transcribe_audio(b"fake-audio")
        assert result["text"] == "hello"
        mock_daemon_client.transcribe_audio.assert_called_once()

    def test_load_model(self, bridge, mock_daemon_client):
        """load_model delegates to load_runtime."""
        result = bridge.load_model("art")
        assert result["status"] == "loaded"
        mock_daemon_client.load_runtime.assert_called_once()

    def test_unload_model(self, bridge, mock_daemon_client):
        """unload_model delegates to unload_runtime."""
        result = bridge.unload_model("art")
        assert result["status"] == "unloaded"
        mock_daemon_client.unload_runtime.assert_called_once()

    def test_model_status(self, bridge, mock_daemon_client):
        """model_status delegates to runtime_status."""
        result = bridge.model_status("art")
        assert result["status"] == "loaded"
        mock_daemon_client.runtime_status.assert_called_once()

    def test_interrupt_llm(self, bridge, mock_daemon_client):
        """interrupt_llm delegates to the daemon client."""
        bridge.interrupt_llm()
        mock_daemon_client.interrupt_llm.assert_called_once()


class TestSignalAPIAdapter:
    """Verify SignalAPIAdapter maps signals to bridge methods."""

    @pytest.fixture
    def mock_bridge(self) -> MagicMock:
        """Return a mocked APIBridge."""
        return MagicMock(spec=APIBridge)

    @pytest.fixture
    def adapter(self, mock_bridge) -> SignalAPIAdapter:
        """Return a SignalAPIAdapter with a mocked bridge."""
        return SignalAPIAdapter(mock_bridge)

    def test_signal_handlers_covers_art_generation(self, adapter):
        """DO_GENERATE_SIGNAL is mapped."""
        handlers = adapter.signal_handlers
        assert SignalCode.DO_GENERATE_SIGNAL in handlers
        assert callable(handlers[SignalCode.DO_GENERATE_SIGNAL])

    def test_signal_handlers_covers_llm_request(self, adapter):
        """LLM_TEXT_GENERATE_REQUEST_SIGNAL is mapped."""
        handlers = adapter.signal_handlers
        assert SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL in handlers
        assert callable(handlers[SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL])

    def test_signal_handlers_covers_tts(self, adapter):
        """TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL is mapped."""
        handlers = adapter.signal_handlers
        assert SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL in handlers

    def test_signal_handlers_covers_stt(self, adapter):
        """AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL is mapped."""
        handlers = adapter.signal_handlers
        assert SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL in handlers

    def test_signal_handlers_covers_interrupt(self, adapter):
        """INTERRUPT_PROCESS_SIGNAL is mapped."""
        handlers = adapter.signal_handlers
        assert SignalCode.INTERRUPT_PROCESS_SIGNAL in handlers

    def test_signal_handlers_covers_model_load(self, adapter):
        """SD_LOAD_SIGNAL, LLM_LOAD_SIGNAL, TTS_ENABLE_SIGNAL are mapped."""
        handlers = adapter.signal_handlers
        assert SignalCode.SD_LOAD_SIGNAL in handlers
        assert SignalCode.LLM_LOAD_SIGNAL in handlers
        assert SignalCode.TTS_ENABLE_SIGNAL in handlers

    def test_signal_handlers_covers_model_unload(self, adapter):
        """SD_UNLOAD_SIGNAL, LLM_UNLOAD_SIGNAL, TTS_DISABLE_SIGNAL are mapped."""
        handlers = adapter.signal_handlers
        assert SignalCode.SD_UNLOAD_SIGNAL in handlers
        assert SignalCode.LLM_UNLOAD_SIGNAL in handlers
        assert SignalCode.TTS_DISABLE_SIGNAL in handlers

    def test_on_do_generate_signal_calls_bridge(self, adapter, mock_bridge):
        """on_do_generate_signal triggers bridge.generate_image_async."""
        data = {"image_request": {"prompt": "test"}}
        adapter.on_do_generate_signal(data)
        mock_bridge.generate_image_async.assert_called_once_with(data)

    def test_on_interrupt_process_signal_calls_bridge(
        self, adapter, mock_bridge
    ):
        """on_interrupt_process_signal triggers bridge.interrupt_llm."""
        adapter.on_interrupt_process_signal({})
        mock_bridge.interrupt_llm.assert_called_once()

    def test_on_load_art_signal_calls_bridge(self, adapter, mock_bridge):
        """on_load_art_signal triggers bridge.load_model('art')."""
        adapter.on_load_art_signal({})
        mock_bridge.load_model.assert_called_once_with(
            "art", deployment_mode="sidecar"
        )


class TestWorkerManagerIntegration:
    """Verify WorkerManager integrates with SignalAPIAdapter."""

    # Use late import to avoid Qt dependency in test environment
    @pytest.mark.skipif(
        "not _has_qt()",
        reason="Qt not available in test environment",
    )
    def test_worker_manager_accepts_adapter(self):
        """WorkerManager constructor accepts signal_api_adapter kwarg."""
        from airunner.components.application.gui.windows.main.worker_manager import (
            WorkerManager,
        )

        adapter = MagicMock(spec=SignalAPIAdapter)
        adapter.signal_handlers = {SignalCode.DO_GENERATE_SIGNAL: MagicMock()}

        wm = WorkerManager(signal_api_adapter=adapter)
        assert wm._signal_api_adapter is adapter
        assert (
            wm.signal_handlers[SignalCode.DO_GENERATE_SIGNAL]
            is adapter.signal_handlers[SignalCode.DO_GENERATE_SIGNAL]
        )

    def test_adapter_optional(self):
        """WorkerManager works without an adapter (backward compatible)."""
        from airunner.components.application.gui.windows.main.worker_manager import (
            WorkerManager,
        )

        wm = WorkerManager()
        assert wm._signal_api_adapter is None
        # Local handlers should still be set
        assert SignalCode.DO_GENERATE_SIGNAL in wm.signal_handlers


def _has_qt() -> bool:
    """Return True when PySide6 is available."""
    try:
        import PySide6  # noqa: F401
        return True
    except ImportError:
        return False
