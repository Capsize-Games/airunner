from sqlalchemy import Column, Integer, String, Float, JSON

from airunner.data.models.base import BaseModel


class User(BaseModel):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, default="User")
    zipcode = Column(String, nullable=True)
    location_display_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    unit_system = Column(String, nullable=True, default="imperial")
    data = Column(JSON, nullable=True)
