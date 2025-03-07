from sqlalchemy import Column, Integer, String, JSON

import datetime

from airunner.data.models.base import BaseModel


class Chatstore(BaseModel):
    __tablename__ = 'chatstore'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_created = Column(String, default=datetime.datetime.now().isoformat())
    key = Column(String, nullable=False, default="")
    value = Column(JSON, nullable=False, default={})
