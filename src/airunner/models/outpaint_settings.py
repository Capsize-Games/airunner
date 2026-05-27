"""Service-owned outpaint settings model."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, LargeBinary

from airunner.base import BaseModel


class OutpaintSettings(BaseModel):
    """Persist layer-scoped outpaint inputs and controls."""

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


__all__ = ["OutpaintSettings"]