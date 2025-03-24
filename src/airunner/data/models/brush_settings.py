from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel
from airunner.settings import AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR, AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR


class BrushSettings(BaseModel):
    __tablename__ = 'brush_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    size = Column(Integer, default=75)
    primary_color = Column(String, default=AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR)
    secondary_color = Column(String, default=AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR)
    strength_slider = Column(Integer, default=950)
    strength = Column(Integer, default=950)
    conditioning_scale = Column(Integer, default=550)
    guidance_scale = Column(Integer, default=75)
