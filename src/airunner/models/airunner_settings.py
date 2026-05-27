"""Service-owned AIRunner settings model."""

from sqlalchemy import JSON, Column, Integer, String

from airunner.base import BaseModel


class AIRunnerSettings(BaseModel):
    """Persist generic named AIRunner settings payloads."""

    __tablename__ = "airunner_settings"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    data = Column(JSON, nullable=False)


__all__ = ["AIRunnerSettings"]