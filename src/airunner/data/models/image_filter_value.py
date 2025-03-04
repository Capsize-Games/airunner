from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from airunner.data.models.base import Base


class ImageFilterValue(Base):
    __tablename__ = 'image_filter_values'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    value_type = Column(String, nullable=False)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    image_filter_id = Column(Integer, ForeignKey('image_filter_settings.id'), nullable=False, default=1)
    image_filter = relationship("ImageFilter", back_populates="image_filter_values")


ImageFilterValue.image_filter = relationship(
    "ImageFilter", 
    back_populates="image_filter_values"
)