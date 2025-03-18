from sqlalchemy import Column, Integer, String, Boolean
from PySide6.QtWidgets import QTabWidget

from airunner.data.models.base import BaseModel
from airunner.data.session_manager import session_scope


class Tab(BaseModel):
    __tablename__ = 'tabs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    section = Column(String, default="")
    name = Column(String, default="")
    active = Column(Boolean, default=False)
    displayed = Column(Boolean, default=True)
    index = Column(Integer, default=0)

    @classmethod
    def update_tabs(
        cls, 
        section: str, 
        tab_widget: QTabWidget, 
        index: int
    ):
        """
        Update the active tab in the database by section.
        """
        tab_text = tab_widget.tabText(index)
        with session_scope() as session:
            session.query(cls).filter(
                cls.section == section
            ).update(
                {cls.active: False}
            )
            session.query(cls).filter(
                cls.section == section,
                cls.name == tab_text
            ).update(
                {cls.active: True}
            )
