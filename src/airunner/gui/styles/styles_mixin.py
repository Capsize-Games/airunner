import os
from pathlib import Path

from airunner.settings import AIRUNNER_DARK_THEME_NAME, AIRUNNER_LIGHT_THEME_NAME


class StylesMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    """
    Dependent on the SettingsMixin being used in the same class
    """
    def set_stylesheet(self):
        """
        Sets the stylesheet for the application based on the current theme
        """
        theme_name = AIRUNNER_DARK_THEME_NAME if self.application_settings.dark_mode_enabled else AIRUNNER_LIGHT_THEME_NAME
        base_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        stylesheet_path = base_dir / theme_name / "styles.qss"

        self.setStyleSheet(
            stylesheet_path.read_text()
            if self.application_settings.override_system_theme
            else ""
        )
