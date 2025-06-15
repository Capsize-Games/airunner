from sqlalchemy import Column, Integer, String

from airunner.components.application.data.base import BaseModel


class Schedulers(BaseModel):
    __tablename__ = "schedulers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
