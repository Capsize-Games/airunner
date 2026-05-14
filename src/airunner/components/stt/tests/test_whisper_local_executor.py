"""Tests for local faster-whisper executor cleanup behavior."""

from unittest.mock import Mock, patch

from airunner.components.stt.executors.whisper_local_executor import (
    WhisperLocalExecutor,
)


def test_unload_model_uses_shared_memory_cleanup():
    executor = WhisperLocalExecutor.__new__(WhisperLocalExecutor)
    executor._model = Mock()
    executor._device = "cuda:0"

    with patch(
        "airunner.components.stt.executors.whisper_local_executor.clear_memory"
    ) as mock_clear:
        WhisperLocalExecutor._unload_model(executor)

    assert executor._model is None
    mock_clear.assert_called_once_with("cuda:0")