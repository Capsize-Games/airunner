from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class STTAPIService(APIServiceBase):
    def audio_processor_response(self, transcription):
        self.emit_signal(
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
            {"transcription": transcription},
        )
