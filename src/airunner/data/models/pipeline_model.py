from sqlalchemy import Column, Integer, String, Boolean

from airunner.data.models.base import Base


class PipelineModel(Base):
    __tablename__ = "pipeline_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_action = Column(String, nullable=False)
    version = Column(String, nullable=False)
    category = Column(String, nullable=False)
    classname = Column(String, nullable=False)
    default = Column(Boolean, nullable=False)
