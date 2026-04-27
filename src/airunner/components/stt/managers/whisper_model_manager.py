from airunner.components.stt.executors.whisper_local_executor import (
    WhisperLocalExecutor,
)


class WhisperModelManager(WhisperLocalExecutor):
    """Compatibility wrapper for the legacy STT manager name."""

    def process_audio(self, audio_data):
        """Preserve the legacy manager API by transcribing and emitting."""
        transcription = self.transcribe(audio_data)
        if transcription:
            self.api.stt.audio_processor_response(transcription)
