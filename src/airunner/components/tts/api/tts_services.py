from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class TTSAPIService(APIServiceBase):
    def play_audio(self, message):
        self.emit_signal(
            SignalCode.TTS_QUEUE_SIGNAL,
            {"message": message, "is_end_of_message": True},
        )

    def toggle(self, enabled):
        self.emit_signal(SignalCode.TOGGLE_TTS_SIGNAL, {"enabled": enabled})

    def start(self):
        self.emit_signal(SignalCode.TTS_ENABLE_SIGNAL, {})

    def stop(self):
        self.emit_signal(SignalCode.TTS_DISABLE_SIGNAL, {})

    def add_to_stream(self, response):
        self.emit_signal(
            SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
            {"message": response},
        )

    def disable(self):
        self.emit_signal(SignalCode.TTS_DISABLE_SIGNAL, {})
