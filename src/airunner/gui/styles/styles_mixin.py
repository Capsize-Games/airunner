import os
from pathlib import Path
from typing import Optional

from airunner.enums import TemplateName
from airunner.settings import (
    AIRUNNER_DARK_THEME_NAME,
    AIRUNNER_LIGHT_THEME_NAME,
)
from airunner.utils.settings import get_qsettings


class StylesMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    """
    Dependent on the SettingsMixin being used in the same class
    """

    def set_stylesheet(
        self,
        template: Optional[TemplateName] = None,
    ):
        """
        Sets the stylesheet for the application based on the current theme

        :param dark_mode: Override the application settings dark mode if provided
        :param override_system_theme: Override the application settings system theme override if provided
        """
        settings = get_qsettings()
        if template is None:
            template_val = settings.value(
                "theme", TemplateName.SYSTEM_DEFAULT.value
            )
            template = TemplateName(template_val)

        theme_map = {
            TemplateName.SYSTEM_DEFAULT: None,
            TemplateName.DARK: AIRUNNER_DARK_THEME_NAME,
            TemplateName.LIGHT: AIRUNNER_LIGHT_THEME_NAME,
            TemplateName.MINT: "mint_theme",
            TemplateName.RAINBOW: "rainbow_theme",
            TemplateName.GITHUB: "github_theme",
            TemplateName.CYBERPUNK: "cyberpunk_theme",
        }

        theme_name = theme_map.get(template, None)

        if theme_name is not None:
            base_dir = Path(os.path.dirname(os.path.realpath(__file__)))
            stylesheet_path = base_dir / theme_name / "styles.qss"
            stylesheet = stylesheet_path.read_text()
        else:
            stylesheet = ""

        self.setStyleSheet(stylesheet)
