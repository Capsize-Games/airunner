import sounddevice as sd

from queue import Queue

from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class TTSVocalizerWorker(Worker):
    """
    Speech (in the form of numpy arrays generated with the TTS class) is added to the
    vocalizer's queue. The vocalizer plays the speech using sounddevice.
    """
    reader_mode_active = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()
        self.stream = sd.OutputStream(samplerate=24000, channels=1)
        self.stream.start()
        self.data = []
        self.started = False
        self.register(SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL, self)
    
    def on_TTSGeneratorWorker_add_to_stream_signal(self, response):
        self.logger.debug("Adding speech to stream...")
        self.add_to_queue(response)

    def handle_message(self, item):
        if item is None:
            self.logger.warning("item is none")
            return
        self.stream.write(item)
        self.started = True
        self.data = []
        
    def handle_speech(self, generated_speech):
        self.logger.info("Adding speech to stream...")
        try:
            self.queue.put(generated_speech)
        except Exception as e:
            self.logger.error(f"Error while adding speech to stream: {e}")
