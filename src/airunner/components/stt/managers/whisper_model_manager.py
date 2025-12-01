import os
import queue

import numpy as np
import torch
from faster_whisper import WhisperModel
from PySide6.QtCore import QThread, QMutex, QObject, Signal

from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.components.art.utils.model_file_checker import ModelFileChecker
from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.settings import (
    AIRUNNER_DEFAULT_STT_HF_PATH,
)


# Audio processing worker that runs in a separate thread
class AudioProcessingWorker(QObject):
    transcription_ready = Signal(str)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.queue = queue.Queue()
        self.running = True

    def process(self):
        """Process audio data from the queue continuously"""
        while self.running:
            try:
                # Get the next audio data from the queue with a timeout
                audio_data = self.queue.get(timeout=0.1)

                if audio_data:
                    item = audio_data["item"]

                    # Convert the byte string to a float32 array
                    inputs = np.frombuffer(item, dtype=np.int16)
                    inputs = inputs.astype(np.float32) / 32767.0

                    transcription = None
                    try:
                        transcription = self.manager._process_inputs(inputs)
                    except Exception as e:
                        self.manager.logger.error(
                            f"Failed to process inputs {e}"
                        )
                        self.manager.logger.error(e)

                    if transcription:
                        self.manager.logger.debug(f"Sending transcription: {transcription}")
                        # Call directly instead of using Qt signal (avoids cross-thread signal issues)
                        self.manager._send_transcription(transcription)

                # Mark this task as done
                self.queue.task_done()

            except queue.Empty:
                # If the queue is empty, just continue and check again
                QThread.msleep(10)  # Small sleep to prevent CPU spinning

    def add_audio(self, audio_data):
        """Add audio data to the processing queue"""
        self.queue.put(audio_data)

    def stop(self):
        """Stop the worker's processing loop"""
        self.running = False


class WhisperModelManager(BaseModelManager):
    """
    Handler for the Whisper model using faster-whisper (CTranslate2).
    Provides ~4x faster transcription compared to transformers-based Whisper.
    """

    def __init__(self, *args, **kwargs):
        self.model_type = ModelType.STT
        self.model_class = "stt"
        self._model_status = {
            ModelType.STT: ModelStatus.UNLOADED,
        }
        super().__init__(*args, **kwargs)

        self._lock = QMutex()
        self._model = None
        self._sampling_rate = 16000
        self.audio_stream = None

        # Setup a single persistent worker thread
        self.worker_thread = QThread()
        self.worker = AudioProcessingWorker(self)
        self.worker.moveToThread(self.worker_thread)
        self.worker.transcription_ready.connect(self._send_transcription)

        # Start the worker thread
        self.worker_thread.started.connect(self.worker.process)
        self.worker_thread.start()

        # Register cleanup for application exit
        self.register(SignalCode.QUIT_APPLICATION, self.cleanup_worker)

        # Determine compute type based on available hardware
        # Use int8 quantization for lower VRAM (~1.5-2GB vs ~3-4GB for float16)
        if torch.cuda.is_available():
            self._device = "cuda"
            self._compute_type = "int8"
        else:
            self._device = "cpu"
            self._compute_type = "int8"

    @property
    def model_path(self) -> str:
        file_path = os.path.expanduser(
            os.path.join(
                self.path_settings.stt_model_path, AIRUNNER_DEFAULT_STT_HF_PATH
            )
        )
        return os.path.abspath(file_path)

    @property
    def stt_is_loading(self) -> bool:
        return self._model_status[ModelType.STT] is ModelStatus.LOADING

    @property
    def stt_is_loaded(self) -> bool:
        return self._model_status[ModelType.STT] is ModelStatus.LOADED

    @property
    def stt_is_unloaded(self) -> bool:
        return self._model_status[ModelType.STT] is ModelStatus.UNLOADED

    @property
    def stt_is_failed(self) -> bool:
        return self._model_status[ModelType.STT] is ModelStatus.FAILED

    def cleanup_worker(self):
        """Clean up the worker thread on application exit"""
        if hasattr(self, "worker") and self.worker:
            self.worker.stop()

        if hasattr(self, "worker_thread") and self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait(
                1000
            )  # Wait up to 1 second for thread to finish

    def process_audio(self, audio_data):
        """
        Process incoming audio data by adding it to the worker's queue
        """
        if hasattr(self, "worker") and self.worker:
            self.worker.add_audio(audio_data)

    def load(self, retry: bool = False):
        if self.stt_is_loading or self.stt_is_loaded:
            return
        self.logger.debug("Loading Whisper (speech-to-text) via faster-whisper")

        # Check for missing files and trigger download if needed
        if not retry:
            should_download, download_info = self._check_and_trigger_download()
            if should_download:
                self.logger.info(
                    "Whisper model files missing, download triggered"
                )
                return False

        self.unload()
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self._load_model()
        # unsure why this is failing to load occasionally - this is a hack
        if self._model is None and retry is False:
            return self.load(retry=True)
        if self._model is not None:
            self.change_model_status(ModelType.STT, ModelStatus.LOADED)
            return True
        else:
            self.change_model_status(ModelType.STT, ModelStatus.FAILED)
            return False

    def unload(self):
        if self.stt_is_loading or self.stt_is_unloaded:
            return
        self.logger.debug("Unloading Whisper (speech-to-text)")
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self._unload_model()
        self.change_model_status(ModelType.STT, ModelStatus.UNLOADED)

    def _load_model(self):
        self.logger.debug(
            f"Loading faster-whisper model from {self.model_path} "
            f"with device={self._device}, compute_type={self._compute_type}"
        )
        try:
            # Clean up any GPU memory before loading to avoid conflicts
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Load the CTranslate2 model directly from local path
            # faster-whisper detects this is a directory and loads locally
            self._model = WhisperModel(
                self.model_path,
                device=self._device,
                compute_type=self._compute_type,
                local_files_only=True,
            )
            self.logger.info(
                f"faster-whisper model loaded on {self._device}"
            )

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self.change_model_status(ModelType.STT, ModelStatus.FAILED)
            return None

    def _unload_model(self):
        del self._model
        self._model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _process_inputs(self, inputs: np.ndarray) -> str:
        """Process audio input array and return transcription using faster-whisper"""
        if not self._model:
            return ""

        try:
            self.logger.debug("Processing audio input with faster-whisper")

            # faster-whisper expects float32 audio normalized to [-1, 1]
            # The AudioProcessingWorker already handles this conversion
            segments, info = self._model.transcribe(
                inputs,
                beam_size=1,
                temperature=self.whisper_settings.temperature,
                vad_filter=True,  # Voice activity detection for better accuracy
            )

            # Collect all segment texts
            transcription = " ".join(segment.text for segment in segments)
            transcription = transcription.strip()

            if not transcription:
                return ""

            self.logger.debug(f"Transcribed: {transcription[:50]}...")
            return transcription

        except Exception as e:
            self.logger.error(f"Error in audio processing: {e}")
            return ""

    def _send_transcription(self, transcription: str):
        """
        Emit the transcription so that other handlers can use it
        """
        self.logger.debug(f"_send_transcription called with: {transcription}")
        self.api.stt.audio_processor_response(transcription)

    def _check_and_trigger_download(self):
        """Check for missing model files and trigger download if needed.

        Returns:
            Tuple of (should_download, download_info)
        """
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
                f"Whisper model files missing: {download_info.get('missing_files', [])}"
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
