from typing import Annotated
from dataclasses import dataclass


@dataclass
class TTSRequest:
    message: Annotated[str, "The message to send to the text-to-speech engine"]
    gender: Annotated[str, "The gender of the voice"] = "Male"


@dataclass
class EspeakTTSRequest(TTSRequest):
    rate: Annotated[int, "Rate of speech in words per minute"] = 100
    pitch: Annotated[int, "Pitch of the voice"] = 100
    volume: Annotated[int, "Volume level"] = 100
    voice: Annotated[str, "Voice to use for speech"] = "male1"
    language: Annotated[str, "Language of the voice"] = "en-US"
