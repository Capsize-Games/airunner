from sqlalchemy import Column, Integer, String, Boolean

from airunner.data.models.base import Base


class ActiveGridSettings(Base):
    __tablename__ = 'active_grid_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, default=True)
    render_border = Column(Boolean, default=True)
    render_fill = Column(Boolean, default=False)
    border_opacity = Column(Integer, default=50)
    fill_opacity = Column(Integer, default=50)
    border_color = Column(String, default="#00FF00")
    fill_color = Column(String, default="#FF0000")
    pos_x = Column(Integer, default=0)
    pos_y = Column(Integer, default=0)
    width = Column(Integer, default=512)
    height = Column(Integer, default=512)