"""Service-owned STT settings model."""

from sqlalchemy import Column, Float, Integer

from airunner_model.base import BaseModel


class STTSettings(BaseModel):
    """Persist speech-to-text runtime settings."""

    __tablename__ = "stt_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    duration = Column(Integer, default=10)
    fs = Column(Integer, default=16000)
    channels = Column(Integer, default=1)
    volume_input_threshold = Column(Float, default=0.08)
    silence_buffer_seconds = Column(Float, default=1.0)
    chunk_duration = Column(Float, default=0.03)


__all__ = ["STTSettings"]