from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class VideoAPIService(APIServiceBase):
    def generate(self, data):
        self.emit_signal(SignalCode.VIDEO_GENERATE_SIGNAL, data)

    def frame_update(self, frame):
        self.emit_signal(
            SignalCode.VIDEO_FRAME_UPDATE_SIGNAL, {"frame": frame}
        )

    def generation_complete(self, path):
        self.emit_signal(SignalCode.VIDEO_GENERATED_SIGNAL, {"path": path})

    def video_generate_step(self, percent, message):
        self.emit_signal(
            SignalCode.VIDEO_PROGRESS_SIGNAL,
            {"percent": percent, "message": message},
        )
