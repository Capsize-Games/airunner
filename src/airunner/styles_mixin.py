import os
from pathlib import Path

from airunner.settings import DARK_THEME_NAME, LIGHT_THEME_NAME


class StylesMixin:
    """
    Dependent on the SettingsMixin being used in the same class
    """
    def set_stylesheet(self):
        """
        Sets the stylesheet for the application based on the current theme
        """
        theme_name = DARK_THEME_NAME if self.application_settings.dark_mode_enabled else LIGHT_THEME_NAME
        base_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        stylesheet_path = base_dir / "styles" / theme_name / "styles.qss"

        self.setStyleSheet(
            stylesheet_path.read_text()
            if self.application_settings.override_system_theme
            else ""
        )
