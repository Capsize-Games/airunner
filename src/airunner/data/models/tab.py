from sqlalchemy import Column, Integer, String, Boolean
from PySide6.QtWidgets import QTabWidget

from airunner.data.models.base import BaseModel
from airunner.data.session_manager import session_scope


class Tab(BaseModel):
    __tablename__ = 'tabs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    section = Column(String, default="", nullable=False)
    name = Column(String, default="", nullable=False)
    active = Column(Boolean, default=False, nullable=False)
    displayed = Column(Boolean, default=True, nullable=False)
    index = Column(Integer, default=0, nullable=False)

    @staticmethod
    def update_tabs(section, tab_widget, index):
        """Update tabs in the database based on the active tab index."""
        # Ensure the index is valid before starting a session
        if index < 0 or index >= tab_widget.count():
            raise IndexError("Tab index out of range.")

        with session_scope() as session:
            # Set all tabs in the section to inactive
            session.query(Tab).filter(Tab.section == section).update({"active": False})

            # Get the tab name at the given index
            tab_name = tab_widget.tabText(index)

            # Set the selected tab to active
            session.query(Tab).filter(Tab.section == section, Tab.name == tab_name).update({"active": True})
            session.commit()
