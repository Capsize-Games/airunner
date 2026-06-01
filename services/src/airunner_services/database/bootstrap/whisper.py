"""Shared bootstrap metadata for Whisper runtime assets."""

from __future__ import annotations

from airunner_services.settings import AIRUNNER_DEFAULT_STT_HF_PATH
from airunner_services.settings import AIRUNNER_DEFAULT_STT_MODEL_FILENAME


WHISPER_FILES = {
    AIRUNNER_DEFAULT_STT_HF_PATH: [AIRUNNER_DEFAULT_STT_MODEL_FILENAME]
}


__all__ = ["WHISPER_FILES"]