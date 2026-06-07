"""Service-owned scheduler metadata model."""

from sqlalchemy import Column, Integer, String

from airunner_services.database.base import BaseModel


class Schedulers(BaseModel):
    """Persisted scheduler rows for art runtimes."""

    __tablename__ = "schedulers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    model_version = Column(String, nullable=True, default="")


__all__ = ["Schedulers"]
