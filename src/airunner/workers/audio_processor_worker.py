from airunner.enums import SignalCode
from airunner.aihandler.stt_handler import STTHandler
from airunner.workers.worker import Worker


class AudioProcessorWorker(Worker):
    """
    This class is responsible for processing audio.
    It will process audio from the audio_queue and send it to the model.
    """ 
    fs = 0

    def __init__(self, prefix):
        super().__init__(prefix=prefix)
        self.stt = STTHandler()

    def handle_message(self, audio_data):
        self.emit_signal(SignalCode.STT_PROCESS_AUDIO_SIGNAL, {
            "message": audio_data
        })
    
    def update_properties(self):
        settings = self.settings
        self.fs = settings["stt_settings"]["fs"]
