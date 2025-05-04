from airunner.enums import SignalCode
from airunner.handlers.stt.whisper_model_manager import WhisperModelManager
from airunner.workers.worker import Worker


class AudioProcessorWorker(Worker):
    """
    This class is responsible for processing audio.
    It will process audio from the audio_queue and send it to the model.
    """

    fs = 0

    def __init__(self):
        self._stt = None
        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.update_properties,
            SignalCode.STT_LOAD_SIGNAL: self.on_stt_load_signal,
            SignalCode.STT_UNLOAD_SIGNAL: self.on_stt_unload_signal,
            SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL: self.on_stt_process_audio_signal,
        }
        super().__init__()

    def start_worker_thread(self):
        self._initialize_stt_handler()
        if self.application_settings.stt_enabled:
            self._stt_load()

    def _initialize_stt_handler(self):
        if self._stt is None:
            self._stt = WhisperModelManager()

    def on_stt_load_signal(self):
        if self._stt is None:
            self._initialize_stt_handler()

        if self._stt:
            self._stt_load()

    def on_stt_unload_signal(self):
        if self._stt:
            self._stt_unload()

    def unload(self):
        self._stt_unload()

    def load(self):
        self._initialize_stt_handler()
        self._stt_load()

    def _stt_load(self):
        if self._stt:
            self._stt.load()
            self.emit_signal(SignalCode.STT_START_CAPTURE_SIGNAL)

    def _stt_unload(self):
        self.emit_signal(SignalCode.STT_STOP_CAPTURE_SIGNAL)
        if self._stt:
            self._stt.unload()

    def on_stt_process_audio_signal(self, message):
        self.add_to_queue(message)

    def handle_message(self, audio_data):
        self._stt.process_audio(audio_data)

    def update_properties(self):
        self.fs = self.stt_settings.fs
