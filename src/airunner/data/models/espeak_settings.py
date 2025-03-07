from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel


class EspeakSettings(BaseModel):
    __tablename__ = 'espeak_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    gender = Column(String, default="Male")
    voice = Column(String, default="male1")
    language = Column(String, default="en-US")
    rate = Column(Integer, default=100)
    pitch = Column(Integer, default=100)
    volume = Column(Integer, default=100)
    punctuation_mode = Column(String, default="none")
