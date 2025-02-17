from sqlalchemy import Column, Integer, String, Float, JSON

from airunner.data.models.base import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    zipcode = Column(String, nullable=True)
    location_display_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    temperature_unit = Column(String, nullable=True, default="fahrenheit")
    wind_speed_unit = Column(String, nullable=True, default="mph")
    precipitation_unit = Column(String, nullable=True, default="inch")
    data = Column(JSON, nullable=True)