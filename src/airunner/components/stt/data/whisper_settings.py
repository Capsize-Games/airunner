from sqlalchemy import Column, Integer, String, Boolean, Float

from airunner.data.models.base import BaseModel


class WhisperSettings(BaseModel):
    __tablename__ = "whisper_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    is_multilingual = Column(Boolean, default=False)
    temperature = Column(Float, default=0.8)
    compression_ratio_threshold = Column(Float, default=1.35)
    logprob_threshold = Column(Float, default=-1.0)
    no_speech_threshold = Column(Float, default=0.2)
    time_precision = Column(Float, default=0.02)
    language = Column(String, default="en")
    task = Column(String, default="transcribe")
