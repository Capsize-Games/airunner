from sqlalchemy import Column, Integer, String, Boolean, Float

from airunner.data.models.base import BaseModel


class GridSettings(BaseModel):
    __tablename__ = 'grid_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_size = Column(Integer, default=64)
    line_width = Column(Integer, default=1)
    line_color = Column(String, default="#101010")
    snap_to_grid = Column(Boolean, default=True)
    canvas_color = Column(String, default="#000000")
    show_grid = Column(Boolean, default=True)
    zoom_level = Column(Float, default=1.0)
    zoom_in_step = Column(Float, default=0.1)
    zoom_out_step = Column(Float, default=0.1)
