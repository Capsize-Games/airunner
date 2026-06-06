"""STT executor backed by the shared runtime registry (legacy adapter).

This executor delegates to ``FasterWhisperSTTExecutor`` for the
actual in-process faster-whisper transcription, preserving the
``STTExecutor`` interface expected by the audio processor worker.
"""

from __future__ import annotations

from typing import Any

from airunner_services.runtimes.stt_executor import STTExecutor
from airunner_services.runtimes.faster_whisper_stt_executor import (
    FasterWhisperSTTExecutor,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger


class RuntimeRegistrySTTExecutor(STTExecutor):
    """Route STT model control and transcription through in-process
    faster-whisper, preserving the registry-compatible interface."""

    def __init__(self) -> None:
        self.logger = get_logger(
            self.__class__.__name__,
            AIRUNNER_LOG_LEVEL,
        )
        self._executor = FasterWhisperSTTExecutor()

    @property
    def stt_is_loaded(self) -> bool:
        """Return whether the executor is ready."""
        return self._executor.stt_is_loaded

    def load(self, retry: bool = False) -> bool:
        """Load the faster-whisper model."""
        return self._executor.load(retry=retry)

    def unload(self) -> None:
        """Release the faster-whisper model."""
        self._executor.unload()

    def transcribe(self, audio_data: Any) -> str:
        """Submit one queued audio payload to faster-whisper."""
        return self._executor.transcribe(audio_data)


__all__ = ["RuntimeRegistrySTTExecutor"]
