from sqlalchemy import Column, Integer, LargeBinary, Boolean

from airunner.data.models.base import BaseModel


class WindowSettings(BaseModel):
    __tablename__ = "window_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    is_maximized = Column(Boolean, default=False)
    is_fullscreen = Column(Boolean, default=False)
    llm_splitter = Column(LargeBinary, nullable=True)
    content_splitter = Column(LargeBinary, nullable=True)
    generator_form_splitter = Column(LargeBinary, nullable=True)
    grid_settings_splitter = Column(LargeBinary, nullable=True)
    tool_tab_widget_index = Column(Integer, default=0)
    width = Column(Integer, default=800)
    height = Column(Integer, default=600)
    x_pos = Column(Integer, default=0)
    y_pos = Column(Integer, default=0)
    mode_tab_widget_index = Column(Integer, default=0)