from PySide6.QtCore import QUrl
from typing import Optional
from airunner.components.home_stage.gui.widgets.home_stage_widget import (
    HomeStageWidget,
)
from airunner.settings import LOCAL_SERVER_PORT, LOCAL_SERVER_HOST
from airunner.utils.location.get_lat_lon import get_lat_lon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot


class WeatherWidget(
    HomeStageWidget,
):
    @property
    def template(self) -> Optional[str]:
        return "weather.jinja2.html"

    @property
    def web_engine_view(self) -> Optional[object]:
        return self.ui.webEngineView
