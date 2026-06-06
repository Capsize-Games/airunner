"""In-process STT executor backed by faster-whisper."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import torch

from airunner_services.runtimes.stt_executor import STTExecutor
from airunner_services.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger


def _load_path_settings() -> Any:
    """Return persisted service-side path settings when available."""
    try:
        from airunner_services.database.models.path_settings import (
            PathSettings,
        )

        return PathSettings.objects.first()
    except Exception:
        return None


def _stt_base_directory(base_path: str, path_settings: Any) -> str:
    """Return the resolved STT model directory used by AIRunner."""
    configured_path = getattr(path_settings, "stt_model_path", "")
    if not configured_path:
        return os.path.join(
            os.path.expanduser(base_path),
            "text/models/stt",
        )
    expanded = os.path.expanduser(str(configured_path))
    if os.path.isabs(expanded):
        return expanded
    return os.path.join(os.path.expanduser(base_path), expanded)


def _discover_model_path(base_path: str, path_settings: Any) -> Optional[str]:
    """Find the first compatible faster-whisper model directory."""
    env_override = os.environ.get("AIRUNNER_WHISPER_MODEL_PATH", "").strip()
    if env_override:
        return os.path.expanduser(env_override)

    configured = _stt_base_directory(base_path, path_settings)
    candidate = Path(os.path.expanduser(configured))

    if candidate.is_dir():
        model_files = list(candidate.glob("*.bin")) + list(
            candidate.glob("*.pt")
        )
        ct2_files = list(candidate.glob("*.ct2"))
        if model_files or ct2_files:
            return str(candidate)
        # Try CTranslate2 subdirectory
        for sub in candidate.iterdir():
            if sub.is_dir() and (
                list(sub.glob("*.bin")) or list(sub.glob("*.pt"))
            ):
                return str(sub)
        # Return directory itself if it looks like a model directory
        config_files = list(candidate.glob("config.json")) + list(
            candidate.glob("tokenizer.json")
        )
        if config_files:
            return str(candidate)

    # Fall back to standard model name
    standard_models = [
        "tiny",
        "tiny.en",
        "base",
        "base.en",
        "small",
        "small.en",
        "medium",
        "medium.en",
        "large-v1",
        "large-v2",
        "large-v3",
    ]
    for model_name in standard_models:
        model_dir = os.path.join(
            os.path.expanduser(base_path),
            "text/models/stt",
            model_name,
        )
        if os.path.isdir(model_dir):
            return model_name

    model_dir = os.path.join(
        os.path.expanduser(base_path),
        "text/models/stt",
    )
    if os.path.isdir(model_dir):
        subdirs = sorted(
            [
                d
                for d in os.listdir(model_dir)
                if os.path.isdir(os.path.join(model_dir, d))
            ]
        )
        if subdirs:
            return os.path.join(model_dir, subdirs[0])
        return str(model_dir)

    return None


def _resolve_device() -> str:
    """Return the torch device string for faster-whisper."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _resolve_compute_type(device: str) -> str:
    """Return the compute type for the given device."""
    if device == "cuda":
        return "float16"
    return "int8"


def discover_model_path() -> Optional[str]:
    """Discover the faster-whisper model path without loading settings."""
    path_settings = _load_path_settings()
    base_path = getattr(
        path_settings,
        "base_path",
        AIRUNNER_BASE_PATH,
    )
    return _discover_model_path(base_path, path_settings)


class FasterWhisperSTTExecutor(STTExecutor):
    """In-process STT executor using faster-whisper.

    Mirrors the approach used by ``ChatGGUF`` for LLM: loads the model
    directly in-process via ``faster-whisper`` rather than spawning a
    native ``whisper.cpp`` binary subprocess.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._model_path: Optional[str] = None
        self._loaded: bool = False
        self.logger = get_logger(
            self.__class__.__name__,
            AIRUNNER_LOG_LEVEL,
        )

    @property
    def stt_is_loaded(self) -> bool:
        """Return whether the model is loaded and ready."""
        return self._loaded and self._model is not None

    def load(self, retry: bool = False) -> bool:
        """Load the faster-whisper model.

        Args:
            retry: Ignored; retained for interface compatibility.

        Returns:
            True when the model loaded successfully.
        """
        if self._loaded and self._model is not None:
            return True
        try:
            path_settings = _load_path_settings()
            base_path = getattr(
                path_settings,
                "base_path",
                AIRUNNER_BASE_PATH,
            )
            model_path = _discover_model_path(base_path, path_settings)
            if model_path is None:
                self.logger.warning(
                    "No STT model found. Downloaded models will be "
                    "picked up on the next load attempt."
                )
                return False

            from faster_whisper import WhisperModel

            device = _resolve_device()
            compute_type = _resolve_compute_type(device)

            self.logger.info(
                "Loading faster-whisper model: path=%s, device=%s, "
                "compute_type=%s",
                model_path,
                device,
                compute_type,
            )
            self._model = WhisperModel(
                model_path,
                device=device,
                compute_type=compute_type,
            )
            self._model_path = model_path
            self._loaded = True
            self.logger.info("faster-whisper model loaded successfully")
            return True
        except ImportError:
            self.logger.error(
                "faster-whisper is not installed. "
                "Install with: pip install faster-whisper"
            )
            return False
        except Exception as exc:
            self.logger.error("Failed to load faster-whisper model: %s", exc)
            self._model = None
            self._loaded = False
            if retry:
                import time

                time.sleep(2)
                return self.load(retry=False)
            return False

    def unload(self) -> None:
        """Release the faster-whisper model."""
        self._model = None
        self._model_path = None
        self._loaded = False

    def transcribe(self, audio_data: Any) -> str:
        """Transcribe one audio payload.

        Args:
            audio_data: Dict with keys:
                - ``item`` (bytes): Raw audio bytes.
                - ``mime_type`` (str, optional): Audio MIME type.
                - ``language`` (str, optional): Language hint.
                - ``sample_rate`` (int, optional): Audio sample rate.

        Returns:
            Transcription text or empty string on failure.
        """
        if not audio_data:
            return ""
        item = audio_data.get("item") if audio_data else None
        if not item:
            return ""
        if not self._loaded or self._model is None:
            self.logger.warning("STT model not loaded, attempting to load now")
            if not self.load():
                return ""

        try:

            audio_array, sample_rate = self._decode_audio(
                item,
                audio_data.get("sample_rate"),
            )
        except Exception as exc:
            self.logger.warning("Audio decode failed: %s", exc)
            return ""

        language = audio_data.get("language") or None
        try:
            segments, info = self._model.transcribe(
                audio_array,
                language=language,
            )
            text = " ".join(segment.text.strip() for segment in segments)
            return text.strip()
        except Exception as exc:
            self.logger.error("faster-whisper transcription failed: %s", exc)
            return ""

    @staticmethod
    def _decode_audio(
        raw_bytes: bytes,
        target_sample_rate: Optional[int],
    ) -> tuple[Any, int]:
        """Decode raw audio bytes into a NumPy float32 array.

        Returns:
            Tuple of (audio_array, sample_rate).
        """
        import io

        import numpy as np
        import soundfile as sf

        audio_file = io.BytesIO(raw_bytes)
        audio_array, sample_rate = sf.read(audio_file, dtype="float32")

        if audio_array.ndim > 1:
            audio_array = np.mean(audio_array, axis=1)

        if target_sample_rate and target_sample_rate != sample_rate:
            import scipy.signal

            duration = len(audio_array) / sample_rate
            new_length = int(duration * target_sample_rate)
            resampled = scipy.signal.resample(
                audio_array.astype(np.float64), new_length
            )
            audio_array = np.asarray(resampled, dtype=np.float32)
            sample_rate = target_sample_rate

        return audio_array, sample_rate


__all__ = ["FasterWhisperSTTExecutor"]
