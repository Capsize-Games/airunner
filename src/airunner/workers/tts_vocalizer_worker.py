import random
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
        self.started = False
        self.register(SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL, self.on_TTSGeneratorWorker_add_to_stream_signal)

    def on_TTSGeneratorWorker_add_to_stream_signal(self, response):
        self.logger.debug("Adding speech to stream...")
        self.add_to_queue(response)

    def handle_message(self, item):
        if item is None:
            self.logger.warning("item is none")
            return

        # Write the item to the stream
        self.stream.write(item)

        # Wait until the stream has finished playing the sound
        #sd.wait()

        self.started = True

        # Pause random between 0.5 to 1 second
        sleep_time = random.randint(1500, 2000)
        self.thread().msleep(sleep_time)

    def handle_speech(self, generated_speech):
        self.logger.info("Adding speech to stream...")
        try:
            self.queue.put(generated_speech)
        except Exception as e:
            self.logger.error(f"Error while adding speech to stream: {e}")
