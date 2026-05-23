"""Service-owned ControlNet settings model."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, LargeBinary, String

from airunner_services.database.base import BaseModel


class ControlnetSettings(BaseModel):
    """Persist layer-scoped ControlNet inputs and tuning values."""

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


__all__ = ["ControlnetSettings"]