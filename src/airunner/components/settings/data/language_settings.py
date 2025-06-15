from sqlalchemy import Column, Integer, String

from airunner.components.data.models.base import BaseModel


class LanguageSettings(BaseModel):
    __tablename__ = "language_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    gui_language = Column(String, nullable=True)
    user_language = Column(String, nullable=True)
    bot_language = Column(String, nullable=True)
