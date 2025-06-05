from sqlalchemy import Column, Integer, Boolean, LargeBinary

from airunner.data.models.base import BaseModel


class ImageToImageSettings(BaseModel):
    __tablename__ = "image_to_image_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(LargeBinary, nullable=True)
    enabled = Column(Boolean, default=False)
    use_grid_image_as_input = Column(Boolean, default=False)
    lock_input_image = Column(Boolean, default=False)
    strength = Column(Integer, default=0)
