from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel
from airunner.enums import SpeechT5Voices


class SpeechT5Settings(BaseModel):
    __tablename__ = "speech_t5_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    datasets_path = Column(String, default="Matthijs/cmu-arctic-xvectors")
    processor_path = Column(String, default="microsoft/speecht5_tts")
    vocoder_path = Column(String, default="microsoft/speecht5_hifigan")
    model_path = Column(String, default="microsoft/speecht5_tts")
    pitch = Column(Integer, default=100)
    voice = Column(String, default=SpeechT5Voices.US_MALE.value)
