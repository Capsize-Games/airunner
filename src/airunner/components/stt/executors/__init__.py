"""Executors for speech-to-text processing backends."""

from airunner.components.stt.executors.stt_executor import STTExecutor
from airunner.components.stt.executors.whisper_local_executor import (
    WhisperLocalExecutor,
)

__all__ = [
    "STTExecutor",
    "WhisperLocalExecutor",
]