from sqlalchemy import Column, Integer, Boolean, String, LargeBinary

from airunner.components.data.models.base import BaseModel


class CanvasLayer(BaseModel):
    __tablename__ = "canvas_layer"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order = Column(Integer, default=0)
    visible = Column(Boolean, default=True)
    locked = Column(Boolean, default=False)
    name = Column(String, default="Layer")
    opacity = Column(Integer, default=100)
    blend_mode = Column(String, default="normal")
    image = Column(LargeBinary, nullable=True)
    mask = Column(LargeBinary, nullable=True)

    # Temporarily commented out relationships to avoid initialization issues
    # TODO: Re-enable after fixing SQLAlchemy relationship mapping
    # relationships will be added back in a future update
