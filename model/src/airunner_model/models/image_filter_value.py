"""Service-owned image filter value model."""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from airunner_model.base import BaseModel


class ImageFilterValue(BaseModel):
    """Persist parameter values for an image filter definition."""

    __tablename__ = "image_filter_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="")
    value = Column(String, nullable=False, default="")
    value_type = Column(String, nullable=False, default="")
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    image_filter_id = Column(
        Integer,
        ForeignKey("image_filter_settings.id"),
        nullable=False,
        default=1,
    )
    image_filter = relationship(
        "ImageFilter",
        back_populates="image_filter_values",
    )


__all__ = ["ImageFilterValue"]