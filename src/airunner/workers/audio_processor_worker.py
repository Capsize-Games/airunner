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
        self.signals = [
            (SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.update_properties)
        ]
        super().__init__(prefix=prefix)
        self.stt = WhisperHandler()

    def handle_message(self, audio_data):
        self.emit_signal(SignalCode.STT_PROCESS_AUDIO_SIGNAL, {
            "message": audio_data
        })
    
    def update_properties(self):
        self.fs = self.stt_settings.fs
