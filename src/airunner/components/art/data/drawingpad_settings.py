from sqlalchemy import Column, Integer, Boolean, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

from airunner.components.data.models.base import BaseModel


class DrawingPadSettings(BaseModel):
    __tablename__ = "drawing_pad_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(
        Integer,
        ForeignKey("canvas_layer.id", ondelete="CASCADE"),
        nullable=True,
    )
    image = Column(LargeBinary, nullable=True)
    mask = Column(LargeBinary, nullable=True)
    enabled = Column(Boolean, default=True)
    enable_automatic_drawing = Column(Boolean, default=False)
    mask_layer_enabled = Column(Boolean, default=False)
    x_pos = Column(Integer, default=0)
    y_pos = Column(Integer, default=0)

    # Relationship to CanvasLayer temporarily commented out
    # TODO: Re-enable after fixing SQLAlchemy relationship mapping
    # layer = relationship("CanvasLayer", back_populates="drawing_pad_settings")

    @property
    def pos(self) -> tuple[int, int]:
        x = self.x_pos if self.x_pos is not None else 0
        y = self.y_pos if self.y_pos is not None else 0
        return x, y
