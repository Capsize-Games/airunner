from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    LargeBinary,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from airunner.components.data.models.base import BaseModel


class ControlnetSettings(BaseModel):
    __tablename__ = "controlnet_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(
        Integer,
        ForeignKey("canvas_layer.id", ondelete="CASCADE"),
        nullable=True,
    )
    image = Column(LargeBinary, nullable=True)
    generated_image = Column(LargeBinary, nullable=True)
    enabled = Column(Boolean, default=False)
    use_grid_image_as_input = Column(Boolean, default=False)
    strength = Column(Integer, default=50)
    conditioning_scale = Column(Integer, default=100)
    guidance_scale = Column(Integer, default=750)
    controlnet = Column(String, default="Canny")
    lock_input_image = Column(Boolean, default=False)

    # Relationship to CanvasLayer temporarily commented out
    # TODO: Re-enable after fixing SQLAlchemy relationship mapping
    # layer = relationship("CanvasLayer", back_populates="controlnet_settings")
