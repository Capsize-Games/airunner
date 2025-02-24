from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from airunner.data.models.base import Base
from airunner.data.models.image_filter_value import ImageFilterValue


class ImageFilter(Base):
    __tablename__ = 'image_filter_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    auto_apply = Column(Boolean, default=False)
    filter_class = Column(String, nullable=False)


ImageFilter.image_filter_values = relationship(
    "ImageFilterValue", 
    order_by=ImageFilterValue.id, 
    back_populates="image_filter"
)