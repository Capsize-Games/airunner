from typing import List
from airunner.utils.settings import get_qsettings


def save_splitter_settings(
    ui: object, splitters: List[str], splitter_name_space: str = "splitters"
) -> None:
    """
    Save the state of splitter widgets to PySide6 application settings.
    """
    settings = get_qsettings()

    print("SAVING SPLITTERS", splitter_name_space)

    for splitter_name in splitters:
        widget = getattr(ui, splitter_name)
        splitter_state = widget.saveState()
        settings.setValue(
            f"{splitter_name_space}/{splitter_name}", splitter_state
        )
