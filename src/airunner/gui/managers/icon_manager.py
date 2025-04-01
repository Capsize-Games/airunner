from typing import List, Tuple
from PySide6 import QtGui
from PySide6.QtGui import QIcon, QPixmap


class IconManager:
    """A class to manage icons for the application."""
    def __init__(self, icons: List[Tuple[str, str]], ui: object):
        """Initialize the IconManager with a list of icons and a UI object."""
        self.icon_cache = {}
        for icon in icons:
            self.icon_cache[icon[0]] = getattr(ui, icon[1])

    def get_icon(self, icon_name, theme) -> QIcon:
        """Get the icon for the given name and theme."""
        key = f"{icon_name}_{theme}"
        if key not in self.icon_cache:
            self.icon_cache[key] = QIcon(
                QPixmap(f":/{theme}/icons/feather/{theme}/{icon_name}.svg")
            )
        return self.icon_cache[key]

    def update_icons(self, theme):
        """Update the icons for the given theme."""
        for icon_name, widget in self.icon_cache.items():
            icon = QtGui.QIcon()
            icon.addPixmap(
                QtGui.QPixmap(
                    f":/{theme}/icons/feather/{theme}/{icon_name}.svg"
                ),
                QtGui.QIcon.Mode.Normal,
                QtGui.QIcon.State.Off)
            widget.setIcon(icon)
