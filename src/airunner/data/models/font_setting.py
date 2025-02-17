from sqlalchemy import Column, Integer, String

from airunner.data.models.base import Base


class FontSetting(Base):
    __tablename__ = "font_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    font_family = Column(String, nullable=False)
    font_size = Column(Integer, nullable=False)
