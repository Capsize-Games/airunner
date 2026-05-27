"""Service-owned drawing pad settings model."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, LargeBinary, String

from airunner.base import BaseModel


class DrawingPadSettings(BaseModel):
    """Persist drawing pad images, masks, and placement state."""

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
    text_items = Column(String, nullable=True)

    @property
    def pos(self) -> tuple[int, int]:
        """Return the persisted drawing pad position."""
        x = self.x_pos if self.x_pos is not None else 0
        y = self.y_pos if self.y_pos is not None else 0
        return x, y


__all__ = ["DrawingPadSettings"]