"""Service-owned ControlNet model metadata."""

from sqlalchemy import Column, Integer, String

from airunner.base import BaseModel


class ControlnetModel(BaseModel):
    """Persisted ControlNet model metadata."""

    __tablename__ = "controlnet_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="")
    path = Column(String, nullable=False, default="")
    display_name = Column(String, nullable=False, default="")
    version = Column(String, nullable=False, default="")


__all__ = ["ControlnetModel"]
