from sqlalchemy import Column, Integer, String, Boolean

from airunner.data.models.base import BaseModel


class PipelineModel(BaseModel):
    __tablename__ = "pipeline_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_action = Column(String, nullable=False, default="")
    version = Column(String, nullable=False, default="")
    category = Column(String, nullable=False, default="")
    classname = Column(String, nullable=False, default="")
    default = Column(Boolean, nullable=False, default=False)
