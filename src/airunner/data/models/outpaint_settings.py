from sqlalchemy import Column, Integer, Boolean, LargeBinary

from airunner.data.models.base import BaseModel


class OutpaintSettings(BaseModel):
    __tablename__ = 'outpaint_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(LargeBinary, nullable=True)
    enabled = Column(Boolean, default=True)
    strength = Column(Integer, default=50)
    mask_blur = Column(Integer, default=0)
    use_grid_image_as_input = Column(Boolean, default=False)
    lock_input_image = Column(Boolean, default=False)
