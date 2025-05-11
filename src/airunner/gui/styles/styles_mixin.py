import os
from pathlib import Path

from airunner.settings import AIRUNNER_DARK_THEME_NAME, AIRUNNER_LIGHT_THEME_NAME


class StylesMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    """
    Dependent on the SettingsMixin being used in the same class
    """
    def set_stylesheet(self, dark_mode=None, override_system_theme=None):
        """
        Sets the stylesheet for the application based on the current theme
        
        :param dark_mode: Override the application settings dark mode if provided
        :param override_system_theme: Override the application settings system theme override if provided
        """
        # Use provided values if they exist, otherwise fall back to application settings
        if dark_mode is None:
            dark_mode = self.application_settings.dark_mode_enabled
        if override_system_theme is None:
            override_system_theme = self.application_settings.override_system_theme
        
        theme_name = AIRUNNER_DARK_THEME_NAME if dark_mode else AIRUNNER_LIGHT_THEME_NAME
        base_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        stylesheet_path = base_dir / theme_name / "styles.qss"

        self.setStyleSheet(
            stylesheet_path.read_text()
            if override_system_theme
            else ""
        )
