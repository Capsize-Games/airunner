from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel


class FontSetting(BaseModel):
    __tablename__ = "font_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="")
    font_family = Column(String, nullable=False, default="")
    font_size = Column(Integer, nullable=False, default=0)
