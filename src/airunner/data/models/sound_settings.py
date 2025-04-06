from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel


class SoundSettings(BaseModel):
    __tablename__ = "sound_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    playback_device = Column(String, default="")
    recording_device = Column(String, default="")
    microphone_volume = Column(
        Integer, default=50
    )
