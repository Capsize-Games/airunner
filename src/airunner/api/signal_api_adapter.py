"""Signal-to-API Adapter — translates legacy SignalCode emissions to API calls.

This adapter acts as a compatibility shim that intercepts signal-based
execution triggers from GUI widgets and reroutes them through the
APIBridge. It is the critical piece enabling phase-by-phase migration:
signals flow through this adapter, which decides whether to use the API
backend or fall back to local workers.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from airunner.api.api_bridge import APIBridge
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

# Type alias for the emit_signal function on the mediator.
EmitFn = Callable[[Any, Dict[str, Any]], None]


class SignalAPIAdapter:
    """Intercepts GUI execution signals and routes them through APIBridge.

    Signal handlers map legacy SignalCode values to APIBridge methods.
    When the API backend is enabled, signals are handled here. When
    disabled, the adapter passes through to the original local handler.
    """

    def __init__(
        self,
        bridge: APIBridge,
        *,
        emit_signal: Optional[EmitFn] = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            bridge: The API bridge instance for backend communication.
            emit_signal: The mediator's emit_signal method for
                dispatching response signals back to GUI widgets.
        """
        self._bridge = bridge
        self._emit = emit_signal or (lambda c, d: None)  # noqa: ARG005

    # ------------------------------------------------------------------
    # Art generation
    # ------------------------------------------------------------------

    def on_do_generate_signal(self, data: Dict[str, Any]) -> None:
        """Handle DO_GENERATE_SIGNAL — route art generation to API."""
        logger.debug(
            "SignalAPIAdapter: routing DO_GENERATE_SIGNAL to API bridge"
        )
        self._bridge.generate_image_async(data)

    def on_interrupt_image_generation_signal(
        self, data: Dict[str, Any]
    ) -> None:
        """Handle INTERRUPT_IMAGE_GENERATION_SIGNAL."""
        job_id = data.get("job_id", "")
        if job_id:
            self._bridge.cancel_generation(job_id)

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def on_llm_request_signal(self, data: Dict[str, Any]) -> None:
        """Handle LLM_TEXT_GENERATE_REQUEST_SIGNAL."""
        logger.debug(
            "SignalAPIAdapter: routing LLM request to API bridge"
        )
        # Extract messages from the legacy data format and call the
        # chat_completion endpoint. The legacy format varies; we handle
        # the common case of a prompt string.
        prompt = data.get("prompt", "")
        if prompt:
            self._bridge.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
        else:
            logger.warning("LLM request signal had no prompt")

    def on_interrupt_process_signal(self, _data: Dict[str, Any]) -> None:
        """Handle INTERRUPT_PROCESS_SIGNAL — interrupt active LLM."""
        self._bridge.interrupt_llm()

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    def on_tts_generate_signal(self, data: Dict[str, Any]) -> None:
        """Handle TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL."""
        text = data.get("text", "")
        voice = data.get("voice")
        if text:
            audio_bytes = self._bridge.synthesize_tts(
                text=text,
                voice=voice,
            )
            # Emit the audio bytes back through the signal system
            self._emit(
                SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
                {"audio": audio_bytes, "text": text},
            )

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------

    def on_stt_transcribe_signal(self, data: Dict[str, Any]) -> None:
        """Handle AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL."""
        audio_bytes = data.get("audio_bytes")
        if audio_bytes:
            result = self._bridge.transcribe_audio(audio_bytes)
            self._emit(
                SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
                result,
            )

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def on_load_art_signal(self, _data: Dict[str, Any]) -> None:
        """Handle SD_LOAD_SIGNAL."""
        self._bridge.load_model("art", deployment_mode="sidecar")

    def on_unload_art_signal(self, _data: Dict[str, Any]) -> None:
        """Handle SD_UNLOAD_SIGNAL."""
        self._bridge.unload_model("art", deployment_mode="sidecar")

    def on_llm_load_signal(self, _data: Dict[str, Any]) -> None:
        """Handle LLM_LOAD_SIGNAL."""
        self._bridge.load_model("llm")

    def on_llm_unload_signal(self, _data: Dict[str, Any]) -> None:
        """Handle LLM_UNLOAD_SIGNAL."""
        self._bridge.unload_model("llm")

    def on_enable_tts_signal(self, _data: Dict[str, Any]) -> None:
        """Handle TTS_ENABLE_SIGNAL."""
        self._bridge.load_model("tts", deployment_mode="sidecar")

    def on_disable_tts_signal(self, _data: Dict[str, Any]) -> None:
        """Handle TTS_DISABLE_SIGNAL."""
        self._bridge.unload_model("tts", deployment_mode="sidecar")

    def on_stt_load_signal(self, _data: Dict[str, Any]) -> None:
        """Handle STT_LOAD_SIGNAL."""
        self._bridge.load_model("stt", deployment_mode="sidecar")

    def on_stt_unload_signal(self, _data: Dict[str, Any]) -> None:
        """Handle STT_UNLOAD_SIGNAL."""
        self._bridge.unload_model("stt", deployment_mode="sidecar")

    # ------------------------------------------------------------------
    # Handler map
    # ------------------------------------------------------------------

    @property
    def signal_handlers(self) -> Dict[Any, Callable[[Dict[str, Any]], None]]:
        """Return the signal-to-API handler mapping.

        This dict can be merged into WorkerManager.signal_handlers to
        intercept execution signals before they reach local workers.
        """
        return {
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: (
                self.on_llm_request_signal
            ),
            SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL: (
                self.on_tts_generate_signal
            ),
            SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL: (
                self.on_stt_transcribe_signal
            ),
            SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL: (
                self.on_interrupt_image_generation_signal
            ),
            SignalCode.INTERRUPT_PROCESS_SIGNAL: (
                self.on_interrupt_process_signal
            ),
            SignalCode.SD_LOAD_SIGNAL: self.on_load_art_signal,
            SignalCode.SD_UNLOAD_SIGNAL: self.on_unload_art_signal,
            SignalCode.LLM_LOAD_SIGNAL: self.on_llm_load_signal,
            SignalCode.LLM_UNLOAD_SIGNAL: self.on_llm_unload_signal,
            SignalCode.TTS_ENABLE_SIGNAL: self.on_enable_tts_signal,
            SignalCode.TTS_DISABLE_SIGNAL: self.on_disable_tts_signal,
            SignalCode.STT_LOAD_SIGNAL: self.on_stt_load_signal,
            SignalCode.STT_UNLOAD_SIGNAL: self.on_stt_unload_signal,
        }
