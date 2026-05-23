class OpenVoiceError(Exception):
    pass


class FileMissing(OpenVoiceError):
    """Raised when a required file is missing."""

    def __init__(self, message=""):
        super().__init__(
            "File not found error during TTS generation. " + message
        )
