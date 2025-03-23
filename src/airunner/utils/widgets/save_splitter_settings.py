from typing import List
from PySide6.QtCore import QSettings

from airunner.settings import (
    AIRUNNER_ORGANIZATION,
    AIRUNNER_APPLICATION_NAME
)


def save_splitter_settings(
    ui: object,
    splitters: List[str]
):
    """
    Save the state of splitter widgets to PySide6 application settings.
    """
    settings = QSettings(AIRUNNER_ORGANIZATION, AIRUNNER_APPLICATION_NAME)

    for splitter_name in splitters:
        widget = getattr(ui, splitter_name)
        sizes = widget.sizes()
    
        valid_state = True
        for size in sizes:
            if size < 50:
                valid_state = False
                break
        
        if valid_state:
            splitter_state = widget.saveState()
            settings.setValue(f"splitters/{splitter_name}", splitter_state)