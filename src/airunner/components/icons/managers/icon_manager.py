import os
from typing import List, Tuple
from PySide6 import QtGui
from PySide6.QtGui import QIcon, QPixmap

from airunner.enums import TemplateName
from airunner.utils.settings import get_qsettings


class IconManager:
    """A class to manage icons for the application."""

    def __init__(self, icons: List[Tuple[str, str]], ui: object):
        """Initialize the IconManager with a list of icons and a UI object."""
        self.icon_cache = {}
        for icon in icons:
            self.icon_cache[icon[1]] = {
                "icon_name": icon[0],
                "widget": getattr(ui, icon[1]),
            }

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
        # icon_cache may contain both metadata dicts (created in __init__)
        # and QIcon instances (created by get_icon). Only process the
        # metadata dict entries which contain the widget and icon name.
        for key, data in self.icon_cache.items():
            if not isinstance(data, dict):
                # Skip cached QIcon or unexpected entries
                continue
            icon_name = data["icon_name"]
            widget = data["widget"]
            icon = QtGui.QIcon()
            icon.addPixmap(
                QtGui.QPixmap(
                    f":/{theme}/icons/feather/{theme}/{icon_name}.svg"
                ),
                QtGui.QIcon.Mode.Normal,
                QtGui.QIcon.State.Off,
            )
            widget.setIcon(icon)

    def set_icons(self):
        """
        Set the icons for the widget which alternate between
        light and dark mode.
        """

        def is_color_dark(hex_color):
            """Return True if the color is dark, False if light."""
            hex_color = hex_color.lstrip("#")
            r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return luminance < 186

        settings = get_qsettings()
        theme = settings.value("theme", TemplateName.SYSTEM_DEFAULT.value)
        theme = theme.lower().replace(" ", "_") + "_theme"
        here = os.path.dirname(os.path.abspath(__file__))
        variables_qss_file_path = os.path.join(
            here, "..", "..", "..", "gui", "styles", theme, "variables.qss"
        )

        dark_color_hex = None
        try:
            with open(variables_qss_file_path, "r") as f:
                for line in f:
                    if "dark-color" in line:
                        # Example: @dark-color: #222222;
                        parts = line.strip().split(":")
                        if len(parts) == 2:
                            value = parts[1].strip().rstrip(";")
                            if value.startswith("#") and len(value) == 7:
                                dark_color_hex = value
                                break
        except Exception as e:
            print(f"Error reading variables.qss: {e}")

        # Fallback if not found
        if not dark_color_hex:
            dark_color_hex = "#222222"

        theme_mode = "dark" if is_color_dark(dark_color_hex) else "light"
        self.update_icons(theme_mode)
