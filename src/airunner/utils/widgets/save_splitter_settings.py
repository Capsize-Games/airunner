from typing import List
from PySide6.QtCore import QSettings


def save_splitter_settings(
    ui: object,
    splitters: List[str]
):
    """
    Save the state of splitter widgets to PySide6 application settings.
    """
    settings = QSettings("YourOrganization", "YourApplication")

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