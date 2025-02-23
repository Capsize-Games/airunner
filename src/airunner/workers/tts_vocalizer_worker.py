import sounddevice as sd
from typing import Optional
from queue import Queue

from PySide6.QtCore import QThread

from airunner.enums import SignalCode
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker


class TTSVocalizerWorker(Worker):
    """
    Speech (in the form of numpy arrays generated with the TTS class) is added to the
    vocalizer's queue. The vocalizer plays the speech using sounddevice.
    """
    reader_mode_active = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, signals = (
            (SignalCode.INTERRUPT_PROCESS_SIGNAL, self.on_interrupt_process_signal),
            (SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL, self.on_unblock_tts_generator_signal),
            (SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL, self.on_TTSGeneratorWorker_add_to_stream_signal),
            (SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal),
        ), **kwargs)
        self.queue = Queue()
        # check if speakers are available
        self.stream = None
        self.start_stream()
        self.started = False
        self.do_interrupt = False
        self.accept_message = True

    def on_interrupt_process_signal(self):
        self.stream.abort()
        self.accept_message = False
        self.queue = Queue()

    def on_unblock_tts_generator_signal(self):
        if self.application_settings.tts_enabled:
            self.logger.debug("Starting TTS stream...")
            self.accept_message = True
            self.stream.start()

    def on_application_settings_changed_signal(self, data):
        if (
            data and
            data.get("setting_name", "") == "speech_t5_settings" and
            data.get("column_name", "") == "pitch"
        ):
            pitch = data.get("value", 0)
            if self.stream is not None:
                self.stream.abort()
                self.start_stream(pitch)

    def start_stream(self, pitch: Optional[int] = None):
        if sd.query_devices(kind='output'):
            if pitch is None:
                pitch = self.speech_t5_settings.pitch
            # set samplerate between 14000 and 24000
            # pitch == 0 -> samplerate == 14000
            # pitch == 50 -> samplerate == 19000
            # pitch == 100 -> samplerate == 24000
            samplerate = 14000 + int(10000.0 * (pitch / 100.0))
            self.stream = sd.OutputStream(samplerate=samplerate, channels=1)
            self.stream.start()

    def on_TTSGeneratorWorker_add_to_stream_signal(self, response: dict):
        if self.accept_message:
            self.logger.debug("Adding speech to stream...")
            self.add_to_queue(response["message"])

    def handle_message(self, item):
        if not self.accept_message:
            return

        if item is None:
            self.logger.warning("item is none")
            return

        if self.stream is None:
            self.start_stream()
            self.logger.warning("No speakers available")
            return

        # Write the item to the stream
        if self.stream is not None and self.stream.active:
            try:
                self.stream.write(item)
            except sd.PortAudioError:
                self.logger.debug("PortAudioError")
            except AttributeError:
                self.logger.debug("stream is None")

            self.started = True
        QThread.msleep(SLEEP_TIME_IN_MS)

    def handle_speech(self, generated_speech):
        self.logger.debug("Adding speech to stream...")
        try:
            self.queue.put(generated_speech)
        except Exception as e:
            self.logger.error(f"Error while adding speech to stream: {e}")
