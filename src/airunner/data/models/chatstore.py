import os

from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base

import datetime

from airunner.data.models.base import Base


class Chatstore(Base):
    __tablename__ = 'chatstore'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_created = Column(String, default=datetime.datetime.now().isoformat())
    key = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
