from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel


class ShortcutKeys(BaseModel):
    __tablename__ = 'shortcut_keys'
    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String, nullable=False, default="")
    text = Column(String, nullable=False, default="")
    key = Column(Integer, nullable=False, default=0)
    modifiers = Column(Integer, nullable=False, default=0)
    description = Column(String, nullable=False, default="")
    signal = Column(String, nullable=False, default="")
