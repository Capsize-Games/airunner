from sqlalchemy import Column, Integer, String, Float

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
    # Expression/naturalness parameters (0-100 scale, mapped to 0.0-1.0)
    # Higher values = more expressive/varied speech
    sdp_ratio = Column(Integer, default=50)  # 50 = 0.5 (stochastic duration predictor ratio)
    noise_scale = Column(Integer, default=80)  # 80 = 0.8 (pitch variation)
    noise_scale_w = Column(Integer, default=90)  # 90 = 0.9 (phoneme duration variation)
