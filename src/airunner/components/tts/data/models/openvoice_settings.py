from sqlalchemy import Column, Integer, String

from airunner.components.data.models.base import BaseModel


class OpenVoiceSettings(BaseModel):
    __tablename__ = "openvoice_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    language = Column(String, default="EN")
    speed = Column(Integer, default=100)
    tone_color = Column(String, default="default")
    pitch = Column(Integer, default=100)
    volume = Column(Integer, default=100)
    voice = Column(String, default="default")
    reference_speaker_path = Column(String, default="default")
