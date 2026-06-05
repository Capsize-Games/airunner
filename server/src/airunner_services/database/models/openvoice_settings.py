"""Service-owned OpenVoice settings model."""

from sqlalchemy import Column, Integer, String

from airunner_services.database.base import BaseModel


class OpenVoiceSettings(BaseModel):
    """Persist OpenVoice synthesis and expression settings."""

    __tablename__ = "openvoice_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    language = Column(String, default="EN")
    speed = Column(Integer, default=100)
    tone_color = Column(String, default="default")
    pitch = Column(Integer, default=100)
    volume = Column(Integer, default=100)
    voice = Column(String, default="default")
    reference_speaker_path = Column(String, default="default")
    sdp_ratio = Column(Integer, default=50)
    noise_scale = Column(Integer, default=80)
    noise_scale_w = Column(Integer, default=90)


__all__ = ["OpenVoiceSettings"]
