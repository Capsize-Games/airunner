from sqlalchemy import Column, Integer, String

from airunner.data.models.base import Base


class ShortcutKeys(Base):
    __tablename__ = 'shortcut_keys'
    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String, nullable=False)
    text = Column(String, nullable=False)
    key = Column(Integer, nullable=False)
    modifiers = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    signal = Column(String, nullable=False)