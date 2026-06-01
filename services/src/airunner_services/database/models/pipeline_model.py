"""Service-owned pipeline metadata model."""

from sqlalchemy import Boolean, Column, Integer, String

from airunner_services.database.base import BaseModel


class PipelineModel(BaseModel):
    """Persisted runtime pipeline metadata."""

    __tablename__ = "pipeline_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_action = Column(String, nullable=False, default="")
    version = Column(String, nullable=False, default="")
    category = Column(String, nullable=False, default="")
    classname = Column(String, nullable=False, default="")
    default = Column(Boolean, nullable=False, default=False)


__all__ = ["PipelineModel"]
