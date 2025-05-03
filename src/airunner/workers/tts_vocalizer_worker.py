import sounddevice as sd
from typing import Optional
from queue import Queue

from PySide6.QtCore import QThread

from airunner.enums import SignalCode, TTSModel
from airunner.settings import AIRUNNER_SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker


class TTSVocalizerWorker(Worker):
    """
    Speech (in the form of numpy arrays generated with the TTS class) is added to the
    vocalizer's queue. The vocalizer plays the speech using sounddevice.
    """

    reader_mode_active = False

    def __init__(self):
        self.signal_handlers = {
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.on_interrupt_process_signal,
            SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL: self.on_unblock_tts_generator_signal,
            SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL: self.on_tts_generator_worker_add_to_stream_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.PLAYBACK_DEVICE_CHANGED: self.on_playback_device_changed_signal,
        }
        super().__init__()
        self.queue = Queue()
        self.started = False
        self.do_interrupt = False
        self.accept_message = True

    @property
    def is_espeak(self) -> bool:
        return self.chatbot_voice_model_type == TTSModel.ESPEAK.value

    def on_interrupt_process_signal(self):
        self.stop_stream()
        self.accept_message = False
        self.queue = Queue()

    def on_unblock_tts_generator_signal(self):
        if self.application_settings.tts_enabled:
            self.logger.debug("Starting TTS stream...")
            self.accept_message = True
            self.start_stream()

    def on_application_settings_changed_signal(self, data):
        if (
            data
            and data.get("setting_name", "") == "speech_t5_settings"
            and data.get("column_name", "") == "pitch"
        ):
            pitch = data.get("value", 0)
            self.stop_stream()
            self.start_stream(pitch)

    def on_playback_device_changed_signal(self):
        self.logger.debug(f"Playback device changed")
        self.stop_stream()
        self.start_stream()

    def stop_stream(self):
        if self.is_espeak:
            return
        self.logger.info("Stopping TTS vocalizer stream...")
        if self.api.sounddevice_manager.out_stream:
            self.api.sounddevice_manager._stop_output_stream()

    def start_stream(self, pitch: Optional[int] = None):
        if self.is_espeak:
            return
        self.logger.info("Starting TTS vocalizer stream...")
        try:
            if sd.query_devices(kind="output"):
                if pitch is None and self.speech_t5_settings is not None:
                    pitch = self.speech_t5_settings.pitch
                else:
                    pitch = 100.0
                # set samplerate between 14000 and 24000
                # pitch == 0 -> samplerate == 14000
                # pitch == 50 -> samplerate == 19000
                # pitch == 100 -> samplerate == 24000
                samplerate = 14000 + int(10000.0 * (pitch / 100.0))
                self._initialize_stream(samplerate)
        except sd.PortAudioError as e:
            self.logger.error(f"Failed to start audio stream: {e}")

    @property
    def playback_device(self):
        playback_device = self.sound_settings.playback_device
        return playback_device if playback_device != "" else "pulse"

    def _initialize_stream(self, samplerate: int):
        self.logger.info(
            f"Initializing TTS stream with samplerate: {samplerate}"
        )
        self.api.sounddevice_manager.initialize_output_stream(
            samplerate=samplerate, channels=1, device_name=self.playback_device
        )

    def on_tts_generator_worker_add_to_stream_signal(self, response: dict):
        if self.accept_message:
            self.logger.debug("Adding speech to stream...")
            self.add_to_queue(response["message"])

    def handle_message(self, item):
        if not self.accept_message:
            return

        if item is None:
            self.logger.warning("item is none")
            return

        if self.api.sounddevice_manager.out_stream is None:
            self.start_stream()
            self.logger.warning("No speakers available")
            return

        # Write the item to the stream
        if self.api.sounddevice_manager.out_stream:
            success = self.api.sounddevice_manager.write_to_output(item)
            if success:
                self.started = True

        QThread.msleep(AIRUNNER_SLEEP_TIME_IN_MS)

    def handle_speech(self, generated_speech):
        self.logger.debug("Adding speech to stream...")
        try:
            self.queue.put(generated_speech)
        except Exception as e:
            self.logger.error(f"Error while adding speech to stream: {e}")
