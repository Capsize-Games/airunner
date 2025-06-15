from sqlalchemy import Column, Integer, String

from airunner.components.data.models.base import BaseModel


class ControlnetModel(BaseModel):
    __tablename__ = "controlnet_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="")
    path = Column(String, nullable=False, default="")
    display_name = Column(String, nullable=False, default="")
    version = Column(String, nullable=False, default="")
