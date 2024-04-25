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
        super().__init__(prefix=prefix)
        self.stt = WhisperHandler()
        self.register(SignalCode.STT_UNLOAD_SIGNAL, self.on_stt_unload_signal)
        self.register(SignalCode.STT_PROCESSOR_UNLOAD_SIGNAL, self.on_stt_processor_unload_signal)
        self.register(SignalCode.STT_FEATURE_EXTRACTOR_UNLOAD_SIGNAL, self.on_stt_feature_extractor_unload_signal)

        self.register(SignalCode.STT_LOAD_SIGNAL, self.on_stt_load_signal)
        self.register(SignalCode.STT_PROCESSOR_LOAD_SIGNAL, self.on_stt_processor_load_signal)
        self.register(SignalCode.STT_FEATURE_EXTRACTOR_LOAD_SIGNAL, self.on_stt_feature_extractor_load_signal)

    def on_stt_unload_signal(self, _message):
        self.stt.unload_model()

    def on_stt_processor_unload_signal(self, _message):
        self.stt.unload_processor()

    def on_stt_feature_extractor_unload_signal(self, _message):
        self.stt.unload_feature_extractor()

    def on_stt_load_signal(self, _message):
        self.stt.load_model()

    def on_stt_processor_load_signal(self, _message):
        self.stt.load_processor()

    def on_stt_feature_extractor_load_signal(self, _message):
        self.stt.load_feature_extractor()

    def handle_message(self, audio_data):
        self.emit_signal(SignalCode.STT_PROCESS_AUDIO_SIGNAL, {
            "message": audio_data
        })
    
    def update_properties(self):
        settings = self.settings
        self.fs = settings["stt_settings"]["fs"]
