from sqlalchemy import Column, Integer, String

from airunner.data.models.base import Base


class Schedulers(Base):
    __tablename__ = 'schedulers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
