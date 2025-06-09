from requests_cache import Dict
from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.enums import SignalCode, TemplateName
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.utils.settings import get_qsettings
import os
import re

try:
    from importlib.metadata import version as pkg_version
except ImportError:
    from importlib_metadata import version as pkg_version  # type: ignore


class HomeStageWidget(BaseWidget):

    widget_class_ = Ui_home_stage_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.REFRESH_STYLESHEET_SIGNAL: self.set_theme,
        }
        super().__init__(*args, **kwargs)

    def showEvent(self, event):
        super().showEvent(event)
        # Render the home page template in the webEngineView
        settings = get_qsettings()
        theme = settings.value("theme", TemplateName.SYSTEM_DEFAULT.value)
        # Get version from installed airunner package
        try:
            version = pkg_version("airunner")
        except Exception:
            version = None
        try:
            # Pass theme variable to Jinja2 template for correct CSS links
            self.render_template(
                self.ui.webEngineView,
                "home.jinja2.html",
                theme=theme.lower(),
                version=version,
            )
            # Also set window.currentTheme for JS
            js = f"window.currentTheme = '{theme.lower()}';"
            self.ui.webEngineView.page().runJavaScript(js)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Failed to render home template: {e}")
            else:
                print(f"Failed to render home template: {e}")

    def set_theme(self, data: Dict):
        """
        Set the theme for the home widget by updating the CSS in the webEngineView.
        This will call the setTheme JS function in the loaded HTML.
        """
        theme_name = data.get(
            "template", TemplateName.SYSTEM_DEFAULT
        ).value.lower()
        if hasattr(self.ui, "webEngineView"):
            # Set window.currentTheme before calling setTheme
            js = f"window.currentTheme = '{theme_name}'; window.setTheme && window.setTheme('{theme_name}');"
            self.ui.webEngineView.page().runJavaScript(js)
