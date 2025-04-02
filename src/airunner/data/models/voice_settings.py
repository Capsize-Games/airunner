from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel


class VoiceSettings(BaseModel):
    __tablename__ = "voice_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    model_type = Column(
        String, nullable=False
    )  # TTSModel string
    settings_id = Column(
        Integer, nullable=False
    )  # Links to EspeakSettings or SpeechT5Settings or OpenVoiceSettings
