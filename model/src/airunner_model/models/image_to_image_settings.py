"""Service-owned image-to-image settings model."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, LargeBinary

from airunner_model.base import BaseModel


class ImageToImageSettings(BaseModel):
    """Persist layer-scoped image-to-image inputs and controls."""

    __tablename__ = "image_to_image_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(
        Integer,
        ForeignKey("canvas_layer.id", ondelete="CASCADE"),
        nullable=True,
    )
    image = Column(LargeBinary, nullable=True)
    enabled = Column(Boolean, default=False)
    use_grid_image_as_input = Column(Boolean, default=False)
    lock_input_image = Column(Boolean, default=False)
    strength = Column(Integer, default=0)


__all__ = ["ImageToImageSettings"]