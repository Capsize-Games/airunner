"""Service-owned voice settings model."""

from sqlalchemy import Column, Integer, String

from airunner_model.base import BaseModel


class VoiceSettings(BaseModel):
    """Persist voice selection and model linkage for TTS."""

    __tablename__ = "voice_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    model_type = Column(String, nullable=False)
    settings_id = Column(Integer, nullable=False)


__all__ = ["VoiceSettings"]