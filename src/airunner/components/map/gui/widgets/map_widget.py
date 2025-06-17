from PySide6.QtCore import QUrl
from typing import Optional
from airunner.components.home_stage.gui.widgets.home_stage_widget import (
    HomeStageWidget,
)
from airunner.settings import LOCAL_SERVER_PORT, LOCAL_SERVER_HOST
from airunner.utils.location.get_lat_lon import get_lat_lon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot


class MapWidgetHandler(QObject):
    """Handles commands from Python to JS for the MapWidget."""

    def __init__(self, map_widget):
        super().__init__()
        self.map_widget = map_widget

    # Optionally, add slots for JS->Python communication if needed


class MapWidget(
    HomeStageWidget,
):
    @property
    def template(self) -> Optional[str]:
        return "map.jinja2.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        url = QUrl(
            f"https://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}/static/html/map.jinja2.html"
        )
        self.ui.webEngineView.setUrl(url)
        self._setup_webchannel()

        self.ui.webEngineView.loadFinished.connect(self._on_page_load_finished)

    def _on_page_load_finished(self, success: bool):
        lat = self.user.latitude or 0.0
        lon = self.user.longitude or 0.0
        self.add_marker(lat, lon)
        self.center_map(lat, lon, zoom=13)

    def _setup_webchannel(self):
        self.handler = MapWidgetHandler(self)
        self.channel = QWebChannel()
        self.channel.registerObject("widgetHandler", self.handler)
        self.ui.webEngineView.page().setWebChannel(self.channel)

    def add_marker(self, lat: float, lon: float) -> None:
        """Add a marker to the map at the given latitude and longitude."""
        js = (
            "if (window.browserAPI) { "
            "window.browserAPI._triggerEvent('map-command', {command: 'addMarker', data: {lat: %s, lon: %s}}); "
            "} else { console.error('browserAPI not found'); }" % (lat, lon)
        )
        self.ui.webEngineView.page().runJavaScript(js)

    def center_map(self, lat: float, lon: float, zoom: int = 13) -> None:
        """Center the map at the given latitude and longitude with the specified zoom."""
        js = (
            "if (window.browserAPI) { "
            "window.browserAPI._triggerEvent('map-command', {command: 'moveMap', data: {lat: %s, lon: %s, zoom: %s}}); "
            "} else { console.error('browserAPI not found'); }"
            % (lat, lon, zoom)
        )
        self.ui.webEngineView.page().runJavaScript(js)
