"""Service-owned sound settings model."""

from sqlalchemy import Column, Integer

from airunner_services.database.base import BaseModel


class SoundSettings(BaseModel):
    """Persist service-owned sound settings."""

    __tablename__ = "sound_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    microphone_volume = Column(Integer, default=50)


__all__ = ["SoundSettings"]
