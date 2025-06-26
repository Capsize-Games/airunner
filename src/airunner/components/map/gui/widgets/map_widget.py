from PySide6.QtCore import QUrl, Signal, Slot
from typing import Optional
from airunner.components.home_stage.gui.widgets.home_stage_widget import (
    HomeStageWidget,
)
from airunner.components.map.gui.widgets.templates.map_ui import Ui_map
from airunner.settings import LOCAL_SERVER_PORT, LOCAL_SERVER_HOST
from airunner.utils.location.get_lat_lon import get_lat_lon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot


class MapWidgetHandler(QObject):
    """Handles commands from Python to JS for the MapWidget and receives search input from JS."""

    def __init__(self, map_widget):
        super().__init__()
        self.map_widget = map_widget

    @Slot(str)
    def onSearchRequested(self, query: str) -> None:
        """Slot called from JS when a map search is requested."""
        self.map_widget.handle_map_search(query)


class MapWidget(
    HomeStageWidget,
):
    widget_class_ = Ui_map

    @property
    def template(self) -> Optional[str]:
        return "map.jinja2.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def handle_map_search(self, query: str) -> None:
        """Handle a map search request from the UI and call the LLM API service."""
        print("handle_map_search query:", query)

        # Try to get coordinates for the location
        try:
            # Check if it's a ZIP code (5 digits) and use the get_lat_lon function
            if query.strip().isdigit() and len(query.strip()) == 5:
                result = get_lat_lon(query.strip())
                lat = result.get("lat")
                lon = result.get("lon")

                if lat is not None and lon is not None:
                    self.center_map(lat, lon, zoom=13)
                    self.add_marker(lat, lon)
                    print(f"Found ZIP code location: {query} at {lat}, {lon}")
                else:
                    print(f"Could not find ZIP code: {query}")
            else:
                # For non-ZIP code searches, we'll need a different geocoding service
                # For now, just print a message and let the LLM API handle it
                print(
                    f"Location search for '{query}' requires a geocoding service (not implemented yet)"
                )

        except Exception as e:
            print(f"Error searching for location '{query}': {e}")

        # Also call the LLM API service if available
        if hasattr(self, "api") and hasattr(self.api, "llm"):
            self.api.llm.map_search(query)

    @Slot()
    def on_searchButton_clicked(self):
        """Handle search button click or Enter key press."""
        query = self.ui.searchLineEdit.text().strip()
        if query:
            self.handle_map_search(query)

    @Slot()
    def on_locateMeButton_clicked(self):
        """Handle locate me button click."""
        lat = self.user.latitude or 0.0
        lon = self.user.longitude or 0.0
        self.center_map(lat, lon, zoom=13)
        self.add_marker(lat, lon)
