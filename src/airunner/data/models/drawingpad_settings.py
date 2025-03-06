from sqlalchemy import Column, Integer, Boolean, LargeBinary

from airunner.data.models.base import BaseModel


class DrawingPadSettings(BaseModel):
    __tablename__ = 'drawing_pad_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(LargeBinary, nullable=True)
    mask = Column(LargeBinary, nullable=True)
    enabled = Column(Boolean, default=True)
    enable_automatic_drawing = Column(Boolean, default=False)
    mask_layer_enabled = Column(Boolean, default=False)
    x_pos = Column(Integer, default=0)
    y_pos = Column(Integer, default=0)