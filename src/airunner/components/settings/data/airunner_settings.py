from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
)
from airunner.components.data.models.base import BaseModel


class AIRunnerSettings(BaseModel):
    __tablename__ = "airunner_settings"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    data = Column(JSON, nullable=False)
