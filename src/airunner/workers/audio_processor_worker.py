from airunner.aihandler.stt.whisper_handler import WhisperHandler
from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class AudioProcessorWorker(Worker):
    """
    This class is responsible for processing audio.
    It will process audio from the audio_queue and send it to the model.
    """ 
    fs = 0

    def __init__(self, prefix):
        super().__init__(prefix=prefix, signals = (
            (SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.update_properties),
        ))
        self.stt = WhisperHandler()

    def on_load_signal(self):
        print("on load tts")
        self.stt.load()
        self.emit_signal(SignalCode.STT_START_CAPTURE_SIGNAL)

    def on_unload_signal(self):
        self.emit_signal(SignalCode.STT_STOP_CAPTURE_SIGNAL)
        self.stt.unload()

    def handle_message(self, audio_data):
        self.stt.on_process_audio({
            "message": audio_data
        })
    
    def update_properties(self):
        self.fs = self.stt_settings.fs
