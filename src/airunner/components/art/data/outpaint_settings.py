from sqlalchemy import Column, Integer, Boolean, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

from airunner.components.data.models.base import BaseModel


class OutpaintSettings(BaseModel):
    __tablename__ = "outpaint_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(
        Integer,
        ForeignKey("canvas_layer.id", ondelete="CASCADE"),
        nullable=True,
    )
    image = Column(LargeBinary, nullable=True)
    enabled = Column(Boolean, default=False)
    strength = Column(Integer, default=50)
    mask_blur = Column(Integer, default=0)
    use_grid_image_as_input = Column(Boolean, default=False)
    lock_input_image = Column(Boolean, default=False)

    # Relationship to CanvasLayer temporarily commented out
    # TODO: Re-enable after fixing SQLAlchemy relationship mapping
    # layer = relationship("CanvasLayer", back_populates="outpaint_settings")
