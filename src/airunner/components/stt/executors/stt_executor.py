"""Interfaces for STT execution backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class STTExecutor(ABC):
    """Execution boundary for speech-to-text backends."""

    @property
    @abstractmethod
    def stt_is_loaded(self) -> bool:
        """Return whether the executor can process audio."""

    @abstractmethod
    def load(self, retry: bool = False) -> bool:
        """Load the executor backend and return success."""

    @abstractmethod
    def unload(self) -> None:
        """Release executor resources."""

    @abstractmethod
    def transcribe(self, audio_data: Any) -> str:
        """Convert one queued audio payload into transcription text."""