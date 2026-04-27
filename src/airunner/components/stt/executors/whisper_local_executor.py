"""Local faster-whisper executor used by the STT worker path."""

from __future__ import annotations

import os

import numpy as np
import torch
from faster_whisper import WhisperModel

from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.components.art.utils.model_file_checker import ModelFileChecker
from airunner.components.stt.executors.stt_executor import STTExecutor
from airunner.enums import ModelStatus, ModelType, SignalCode
from airunner.settings import AIRUNNER_DEFAULT_STT_HF_PATH


class WhisperLocalExecutor(BaseModelManager, STTExecutor):
    """In-process faster-whisper executor behind an explicit boundary."""

    def __init__(self, *args, **kwargs):
        self.model_type = ModelType.STT
        self.model_class = "stt"
        self._model_status = {
            ModelType.STT: ModelStatus.UNLOADED,
        }
        super().__init__(*args, **kwargs)
        self._model = None
        self._sampling_rate = 16000
        self.audio_stream = None
        self.register(SignalCode.QUIT_APPLICATION, self.unload)

        if torch.cuda.is_available():
            self._device = "cuda"
            self._compute_type = "int8"
        else:
            self._device = "cpu"
            self._compute_type = "int8"

    @property
    def model_path(self) -> str:
        """Return the local model directory used by faster-whisper."""
        file_path = os.path.expanduser(
            os.path.join(
                self.path_settings.stt_model_path,
                AIRUNNER_DEFAULT_STT_HF_PATH,
            )
        )
        return os.path.abspath(file_path)

    @property
    def stt_is_loading(self) -> bool:
        """Return whether the STT executor is loading."""
        return self._model_status[ModelType.STT] is ModelStatus.LOADING

    @property
    def stt_is_loaded(self) -> bool:
        """Return whether the STT executor is ready."""
        return self._model_status[ModelType.STT] is ModelStatus.LOADED

    @property
    def stt_is_unloaded(self) -> bool:
        """Return whether the STT executor is unloaded."""
        return self._model_status[ModelType.STT] is ModelStatus.UNLOADED

    @property
    def stt_is_failed(self) -> bool:
        """Return whether the STT executor failed to load."""
        return self._model_status[ModelType.STT] is ModelStatus.FAILED

    def load(self, retry: bool = False) -> bool:
        """Load the faster-whisper model when needed."""
        if self.stt_is_loaded:
            return True
        if self.stt_is_loading:
            return False
        self.logger.debug("Loading Whisper (speech-to-text) via faster-whisper")

        if not retry:
            should_download, _download_info = self._check_and_trigger_download()
            if should_download:
                self.logger.info(
                    "Whisper model files missing, download triggered"
                )
                return False

        self.unload()
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self._load_model()
        if self._model is None and retry is False:
            self.change_model_status(ModelType.STT, ModelStatus.UNLOADED)
            return self.load(retry=True)
        if self._model is not None:
            self.change_model_status(ModelType.STT, ModelStatus.LOADED)
            return True
        self.change_model_status(ModelType.STT, ModelStatus.FAILED)
        return False

    def unload(self) -> None:
        """Unload the active faster-whisper model if present."""
        if self.stt_is_loading or self.stt_is_unloaded:
            return
        self.logger.debug("Unloading Whisper (speech-to-text)")
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self._unload_model()
        self.change_model_status(ModelType.STT, ModelStatus.UNLOADED)

    def transcribe(self, audio_data) -> str:
        """Transcribe one queued audio payload synchronously."""
        if not self._model or not audio_data:
            return ""

        item = audio_data.get("item")
        if not item:
            return ""

        inputs = np.frombuffer(item, dtype=np.int16)
        inputs = inputs.astype(np.float32) / 32767.0
        return self._process_inputs(inputs)

    def _load_model(self):
        """Instantiate the local faster-whisper model."""
        self.logger.debug(
            f"Loading faster-whisper model from {self.model_path} "
            f"with device={self._device}, compute_type={self._compute_type}"
        )
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._model = WhisperModel(
                self.model_path,
                device=self._device,
                compute_type=self._compute_type,
                local_files_only=True,
            )
            self.logger.info(
                f"faster-whisper model loaded on {self._device}"
            )

        except Exception as exc:
            self.logger.error(f"Failed to load model: {exc}")
            self.change_model_status(ModelType.STT, ModelStatus.FAILED)
            return None

    def _unload_model(self):
        """Release the loaded faster-whisper model."""
        if self._model is not None:
            del self._model
        self._model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _process_inputs(self, inputs: np.ndarray) -> str:
        """Run faster-whisper transcription on normalized audio samples."""
        if not self._model:
            return ""

        try:
            self.logger.debug("Processing audio input with faster-whisper")
            segments, _info = self._model.transcribe(
                inputs,
                beam_size=1,
                temperature=self.whisper_settings.temperature,
                vad_filter=True,
            )
            transcription = " ".join(segment.text for segment in segments)
            transcription = transcription.strip()
            if not transcription:
                return ""
            self.logger.debug(f"Transcribed: {transcription[:50]}...")
            return transcription
        except Exception as exc:
            self.logger.error(f"Error in audio processing: {exc}")
            return ""

    def _check_and_trigger_download(self):
        """Check model files and request a download when required."""
        model_path = self.model_path
        model_id = AIRUNNER_DEFAULT_STT_HF_PATH

        should_download, download_info = (
            ModelFileChecker.should_trigger_download(
                model_path=model_path,
                model_type="stt",
                model_id=model_id,
            )
        )

        if should_download:
            self.logger.info(
                "Whisper model files missing: %s",
                download_info.get("missing_files", []),
            )
            self.emit_signal(
                SignalCode.START_HUGGINGFACE_DOWNLOAD,
                {
                    "repo_id": download_info["repo_id"],
                    "model_path": model_path,
                    "model_type": "stt",
                    "callback": lambda: self.load(retry=True),
                },
            )

        return should_download, download_info