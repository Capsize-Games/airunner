"""Service-owned language settings model."""

from sqlalchemy import Column, Integer, String

from airunner_services.database.base import BaseModel


class LanguageSettings(BaseModel):
    """Persist service-owned conversation language preferences."""

    __tablename__ = "language_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_language = Column(String, nullable=True)
    bot_language = Column(String, nullable=True)


__all__ = ["LanguageSettings"]
