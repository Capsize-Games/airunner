from typing import Optional
from requests_cache import Dict
from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.enums import TemplateName
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.utils.settings import get_qsettings

try:
    from importlib.metadata import version as pkg_version
except ImportError:
    from importlib_metadata import version as pkg_version  # type: ignore


class HomeStageWidget(BaseWidget):
    widget_class_ = Ui_home_stage_widget

    @property
    def web_engine_view(self) -> Optional[object]:
        return self.ui.webEngineView

    @property
    def template(self) -> Optional[str]:
        return "home.jinja2.html"

    @property
    def template_context(self) -> Dict:
        context = super().template_context
        context["version"] = pkg_version("airunner")
        return context

    def on_theme_changed_signal(self, data: Dict):
        """
        Set the theme for the home widget by updating the CSS in the webEngineView.
        This will call the setTheme JS function in the loaded HTML.
        """
        if hasattr(self.ui, "webEngineView"):
            theme_name = data.get(
                "template", TemplateName.SYSTEM_DEFAULT
            ).value.lower()
            # Set window.currentTheme before calling setTheme
            js = f"window.currentTheme = '{theme_name}'; window.setTheme && window.setTheme('{theme_name}');"
            self.ui.webEngineView.page().runJavaScript(js)
        super().on_theme_changed_signal(data)
