from airunner.components.stt.executors.whisper_local_executor import (
    WhisperLocalExecutor,
)
from airunner.components.stt.executors.stt_executor import STTExecutor
from airunner.enums import SignalCode
from airunner.components.application.workers.worker import Worker


class AudioProcessorWorker(Worker):
    """
    This class is responsible for processing audio.
    It will process audio from the audio_queue and send it to the model.
    """

    fs = 0

    def __init__(self):
        self._executor = None
        super().__init__()

    def start_worker_thread(self):
        self._initialize_stt_handler()
        if self.application_settings.stt_enabled:
            self._stt_load()

    def _initialize_stt_handler(self):
        if self._executor is None:
            self._executor = self._create_stt_executor()

    def _create_stt_executor(self) -> STTExecutor:
        """Create the local STT executor used by the processor worker."""
        return WhisperLocalExecutor()

    def on_stt_load_signal(self, data: dict = None):
        if self._executor is None:
            self._initialize_stt_handler()

        if self._executor:
            self._stt_load()

    def on_stt_unload_signal(self, data: dict = None):
        if self._executor:
            self._stt_unload()

    def unload(self):
        self._stt_unload()

    def load(self):
        self._initialize_stt_handler()
        self._stt_load()

    def _stt_load(self):
        if self._executor:
            self._executor.load()
            self.emit_signal(SignalCode.STT_START_CAPTURE_SIGNAL)

    def _stt_unload(self):
        self.emit_signal(SignalCode.STT_STOP_CAPTURE_SIGNAL)
        if self._executor:
            self._executor.unload()

    def on_stt_process_audio_signal(self, message):
        self.logger.debug(f"on_stt_process_audio_signal called, message keys: {message.keys() if message else 'None'}")
        self.add_to_queue(message)

    def handle_message(self, audio_data):
        self.logger.debug(
            f"handle_message called, _executor={self._executor}, "
            f"audio_data keys: {audio_data.keys() if audio_data else 'None'}"
        )
        if self._executor is None:
            self.logger.warning("STT handler not initialized, skipping audio")
            return
        if not self._executor.stt_is_loaded:
            self.logger.warning("STT model not loaded, skipping audio")
            return
        self.logger.debug("Processing audio through STT executor")
        transcription = self._executor.transcribe(audio_data)
        if transcription:
            self.api.stt.audio_processor_response(transcription)

    def update_properties(self):
        self.fs = self.stt_settings.fs
