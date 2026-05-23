"""Service-owned user model."""

from sqlalchemy import Column, Float, Integer, JSON, String

from airunner_model.base import BaseModel


class User(BaseModel):
    """Persisted end-user profile data used by conversations and tools."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, default="User")
    zipcode = Column(String, nullable=True)
    location_display_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    unit_system = Column(String, nullable=True, default="imperial")
    data = Column(JSON, nullable=True)


__all__ = ["User"]