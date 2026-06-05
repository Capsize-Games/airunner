"""Service-owned TTS request dataclasses."""

from dataclasses import dataclass
from typing import Annotated

from airunner_services.contract_enums import AvailableLanguage


@dataclass
class TTSRequest:
    """Base TTS request payload."""

    message: Annotated[str, "The message to send to the text-to-speech engine"]
    gender: Annotated[str, "The gender of the voice"] = "Male"
    language: Annotated[AvailableLanguage, "Language of the voice"] = (
        AvailableLanguage.EN
    )


@dataclass
class EspeakTTSRequest(TTSRequest):
    """TTS request for the espeak-based backend."""

    rate: Annotated[int, "Rate of speech in words per minute"] = 100
    pitch: Annotated[int, "Pitch of the voice"] = 100
    volume: Annotated[int, "Volume level"] = 100
    voice: Annotated[str, "Voice to use for speech"] = "male1"
    language: Annotated[str, "Language of the voice"] = "en-US"


@dataclass
class OpenVoiceTTSRequest(TTSRequest):
    """TTS request for the OpenVoice backend."""

    language: Annotated[str, "Language of the voice"] = "EN"
    speed: Annotated[int, "Speed of speech"] = 100
    tone_color: Annotated[str, "Tone color of the voice"] = "default"
    pitch: Annotated[int, "Pitch of the voice"] = 100
    volume: Annotated[int, "Volume level"] = 100
    voice: Annotated[str, "Voice to use for speech"] = "default"


__all__ = ["EspeakTTSRequest", "OpenVoiceTTSRequest", "TTSRequest"]
