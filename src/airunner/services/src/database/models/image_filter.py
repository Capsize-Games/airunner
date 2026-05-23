"""Service-owned image filter model."""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from airunner_services.database.base import BaseModel


class ImageFilter(BaseModel):
    """Persist image filter definitions and their configuration values."""

    __tablename__ = "image_filter_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="")
    display_name = Column(String, nullable=False, default="")
    auto_apply = Column(Boolean, default=False)
    filter_class = Column(String, nullable=False, default="")

    image_filter_values = relationship(
        "ImageFilterValue",
        order_by="ImageFilterValue.id",
        back_populates="image_filter",
    )


__all__ = ["ImageFilter"]