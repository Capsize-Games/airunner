from PySide6.QtCore import Slot
from typing import Optional

from mistralai import Dict
from airunner.components.home_stage.gui.widgets.home_stage_widget import (
    HomeStageWidget,
)
from airunner.components.map.gui.widgets.templates.map_ui import Ui_map
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot
from airunner.enums import SignalCode
from PySide6.QtCore import QEventLoop


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
        self._event_loop = None
        self._pending_map_result = None
        self._pending_map_query = None
        self.signal_handlers = {
            SignalCode.MAP_SEARCH_RESULT_SIGNAL: self._on_llm_signal,
        }
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

    def add_marker(self, lat: float, lon: float, label: str = None) -> None:
        """Add a marker to the map at the given latitude and longitude."""
        js = (
            "if (window.browserAPI) { "
            "window.browserAPI._triggerEvent('map-command', {command: 'addMarker', data: {lat: %s, lon: %s, label: %s}}); "
            "} else { console.error('browserAPI not found'); }"
            % (lat, lon, f"'{label}'" if label else "null")
        )
        self.ui.webEngineView.page().runJavaScript(js)

    def clear_markers(self) -> None:
        """Clear all markers from the map."""
        js = (
            "if (window.browserAPI) { "
            "window.browserAPI._triggerEvent('map-command', {command: 'clearMarkers', data: {}}); "
            "} else { console.error('browserAPI not found'); }"
        )
        self.ui.webEngineView.page().runJavaScript(js)

    def add_route_path(
        self, coordinates: list, color: str = "#3388ff", weight: int = 5
    ) -> None:
        """Add a route path (polyline) to the map using an array of [lat, lon] coordinates."""
        import json

        print(
            f"[MapWidget] add_route_path called with {len(coordinates)} coordinates"
        )
        print(
            f"[MapWidget] First few coordinates: {coordinates[:3] if len(coordinates) > 3 else coordinates}"
        )
        print(f"[MapWidget] Color: {color}, Weight: {weight}")

        # Properly serialize coordinates as JSON
        coordinates_json = json.dumps(coordinates)

        js = (
            "if (window.browserAPI) { "
            f"window.browserAPI._triggerEvent('map-command', {{command: 'addRoutePath', data: {{coordinates: {coordinates_json}, color: '{color}', weight: {weight}}}}}); "
            "} else { console.error('browserAPI not found'); }"
        )
        print(f"[MapWidget] Executing JavaScript: {js[:200]}...")
        self.ui.webEngineView.page().runJavaScript(js)

    def clear_route_paths(self) -> None:
        """Clear all route paths from the map."""
        js = (
            "if (window.browserAPI) { "
            "window.browserAPI._triggerEvent('map-command', {command: 'clearRoutePaths', data: {}}); "
            "} else { console.error('browserAPI not found'); }"
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
        """Handle a map search request from the UI and call the MapAgent LLM service."""
        print(f"[MapWidget] handle_map_search called with query: {query}")
        self._pending_map_query = query
        self._pending_map_result = None
        self._event_loop = QEventLoop()
        self.api.llm.map_search(query)

        # QTimer.singleShot(5000, self._event_loop.quit)  # 5s timeout
        # self._event_loop.exec()
        # map_tool_result = self._pending_map_result
        # if not map_tool_result:
        #     print(f"[MapWidget] No map tool result from agent. Query: {query}")
        #     print(
        #         f"[MapWidget] _pending_map_result: {self._pending_map_result}"
        #     )
        #     print(f"[MapWidget] _pending_map_query: {self._pending_map_query}")
        #     return
        # print(f"[MapWidget] map_tool_result received: {map_tool_result}")

    def _handle_map_search_result(self, map_tool_result):
        # Handle different types of map results
        lat = None
        lon = None

        if isinstance(map_tool_result, dict):
            # Check if this is a directions result with start/end points
            if "start" in map_tool_result and "end" in map_tool_result:
                print(
                    f"[MapWidget] Handling directions result: {map_tool_result}"
                )

                # Clear existing markers and route paths first for directions
                self.clear_markers()
                self.clear_route_paths()

                start = map_tool_result["start"]
                end = map_tool_result["end"]

                # Add markers for both start and end points
                if "lat" in start and "lon" in start:
                    start_lat = float(start["lat"])
                    start_lon = float(start["lon"])
                    start_name = start.get("display_name", "Start")
                    self.add_marker(
                        start_lat, start_lon, f"Start: {start_name}"
                    )
                    print(
                        f"[MapWidget] Added start marker at {start_lat}, {start_lon}"
                    )

                if "lat" in end and "lon" in end:
                    end_lat = float(end["lat"])
                    end_lon = float(end["lon"])
                    end_name = end.get("display_name", "End")
                    self.add_marker(end_lat, end_lon, f"End: {end_name}")
                    print(
                        f"[MapWidget] Added end marker at {end_lat}, {end_lon}"
                    )

                # Draw the route path if available
                if "path" in map_tool_result and map_tool_result["path"]:
                    path_coordinates = map_tool_result["path"]
                    print(
                        f"[MapWidget] Drawing route path with {len(path_coordinates)} coordinate pairs"
                    )
                    print(
                        f"[MapWidget] Raw path coordinates (first 3): {path_coordinates[:3] if len(path_coordinates) > 3 else path_coordinates}"
                    )

                    # Convert from [[lon, lat], [lon, lat], ...] to [[lat, lon], [lat, lon], ...]
                    # OSRM returns coordinates as [longitude, latitude] but Leaflet expects [latitude, longitude]
                    leaflet_coordinates = [
                        [coord[1], coord[0]] for coord in path_coordinates
                    ]

                    print(
                        f"[MapWidget] Transformed leaflet coordinates (first 3): {leaflet_coordinates[:3] if len(leaflet_coordinates) > 3 else leaflet_coordinates}"
                    )
                    print(
                        f"[MapWidget] Total coordinates to send: {len(leaflet_coordinates)}"
                    )

                    self.add_route_path(
                        leaflet_coordinates, color="#FF6B35", weight=4
                    )
                    print(f"[MapWidget] Route path drawn successfully")
                else:
                    print(
                        f"[MapWidget] No path data available in map_tool_result"
                    )

                # Center map to show both points (use start point for centering if no path)
                if (
                    "lat" in start
                    and "lon" in start
                    and not map_tool_result.get("path")
                ):
                    lat = float(start["lat"])
                    lon = float(start["lon"])
                    self.center_map(lat, lon, zoom=6)  # Zoom out to show route
                    print(
                        f"[MapWidget] Centered map on start location: {lat}, {lon}"
                    )

                # Show distance info if available
                if "distance_miles" in map_tool_result:
                    distance = map_tool_result["distance_miles"]
                    print(f"[MapWidget] Route distance: {distance} miles")

                return

            # Handle simple location search results (existing logic)
            lat = (
                float(map_tool_result.get("lat"))
                if map_tool_result.get("lat")
                else None
            )
            lon = (
                float(map_tool_result.get("lon"))
                if map_tool_result.get("lon")
                else None
            )
            print("LAT", lat, "LON", lon)
            display_name = map_tool_result.get("display_name")
            boundingbox = map_tool_result.get("boundingbox")

            # Show marker at city center
            if lat is not None and lon is not None:
                # Clear previous markers and route paths for single location search
                self.clear_markers()
                self.clear_route_paths()
                marker_label = display_name or f"Location: {lat}, {lon}"
                self.add_marker(lat, lon, marker_label)
                self.center_map(lat, lon, zoom=11)

            # Draw bounding box if available
            if boundingbox and len(boundingbox) == 4:
                try:
                    south = float(boundingbox[0])
                    north = float(boundingbox[1])
                    west = float(boundingbox[2])
                    east = float(boundingbox[3])
                    # Draw rectangle (implement JS call or overlay as needed)
                    js = f"if (window.browserAPI) {{ window.browserAPI._triggerEvent('map-command', {{command: 'drawBoundingBox', data: {{south: {south}, north: {north}, west: {west}, east: {east}}}}}); }}"
                    self.ui.webEngineView.page().runJavaScript(js)
                except Exception as e:
                    print(f"[MapWidget] Error drawing bounding box: {e}")
            return
        # ...existing code for search_type branching...

    def _on_llm_signal(self, data: Dict):
        self._handle_map_search_result(data.get("result", {}))

    def geocode_location(self, query: str):
        """Geocode a location using Nominatim."""
        from airunner.settings import AIRUNNER_NOMINATIM_URL
        import requests

        url = (
            f"{AIRUNNER_NOMINATIM_URL.rstrip('/')}/search"
            if AIRUNNER_NOMINATIM_URL
            else "https://nominatim.openstreetmap.org/search"
        )
        params = {"q": query, "format": "json", "limit": 1}
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception as e:
            print(f"Geocoding error: {e}")
        return None, None

    def search_poi(self, poi_type: str, lat: float = None, lon: float = None):
        """Search for POIs using Nominatim (amenity/tourism)."""
        from airunner.settings import AIRUNNER_NOMINATIM_URL
        import requests

        url = (
            f"{AIRUNNER_NOMINATIM_URL.rstrip('/')}/search"
            if AIRUNNER_NOMINATIM_URL
            else "https://nominatim.openstreetmap.org/search"
        )
        params = {"q": poi_type, "format": "json", "limit": 10}
        if lat is not None and lon is not None:
            params["viewbox"] = f"{lon-0.05},{lat-0.05},{lon+0.05},{lat+0.05}"
            params["bounded"] = 1
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return [
                {"lat": float(r["lat"]), "lon": float(r["lon"])}
                for r in results
            ]
        except Exception as e:
            print(f"POI search error: {e}")
        return []

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
