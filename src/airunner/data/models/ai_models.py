from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from airunner.data.models.base import Base


class AIModels(Base):
    __tablename__ = 'aimodels'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    version = Column(String, nullable=False)
    category = Column(String, nullable=False)
    pipeline_action = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False)
    model_type = Column(String, nullable=False)
    is_default = Column(Boolean, nullable=False)
    generator_settings = relationship("GeneratorSettings", back_populates="aimodel")