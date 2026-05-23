"""Service-owned scheduler metadata model."""

from sqlalchemy import Column, Integer, String

from airunner_model.base import BaseModel


class Schedulers(BaseModel):
    """Persisted scheduler rows for art runtimes."""

    __tablename__ = "schedulers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    display_name = Column(String, nullable=True)


__all__ = ["Schedulers"]
