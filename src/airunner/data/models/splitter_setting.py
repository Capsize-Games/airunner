from sqlalchemy import Column, Integer, LargeBinary, String

from airunner.data.models.base import BaseModel


class SplitterSetting(BaseModel):
    __tablename__ = "splitter_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True, unique=True)
    splitter_settings = Column(LargeBinary, nullable=True)