from sqlalchemy import JSON, Column, Integer, String

from airunner.components.data.models.base import BaseModel


class Tool(BaseModel):
    __tablename__ = "tools"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    data = Column(String, nullable=False)
    description = Column(String, nullable=True)
    props = Column(JSON, nullable=True, default={})
