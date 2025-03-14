from sqlalchemy import Column, Integer, String, Boolean, LargeBinary

from airunner.data.models.base import BaseModel


class ControlnetSettings(BaseModel):
    __tablename__ = 'controlnet_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(LargeBinary, nullable=True)
    generated_image = Column(LargeBinary, nullable=True)
    enabled = Column(Boolean, default=False)
    use_grid_image_as_input = Column(Boolean, default=False)
    strength = Column(Integer, default=50)
    conditioning_scale = Column(Integer, default=100)
    guidance_scale = Column(Integer, default=750)
    controlnet = Column(String, default="Canny")
    lock_input_image = Column(Boolean, default=False)
