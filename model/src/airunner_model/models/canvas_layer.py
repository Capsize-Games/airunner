"""Service-owned canvas layer model."""

from sqlalchemy import Boolean, Column, Integer, String

from airunner_model.base import BaseModel


class CanvasLayer(BaseModel):
    """Persist canvas layer metadata for the drawing stack."""

    __tablename__ = "canvas_layer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order = Column(Integer, default=0)
    visible = Column(Boolean, default=True)
    locked = Column(Boolean, default=False)
    name = Column(String, default="Layer", unique=True)
    opacity = Column(Integer, default=100)
    blend_mode = Column(String, default="normal")


__all__ = ["CanvasLayer"]