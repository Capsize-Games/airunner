from sqlalchemy import Column, Integer, String

from airunner.data.models.base import Base


class ControlnetModel(Base):
    __tablename__ = "controlnet_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
