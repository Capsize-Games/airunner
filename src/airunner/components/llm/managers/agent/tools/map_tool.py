"""
MapTool: LLM Tool Integration for Map/Nominatim/Leaflet Actions

This tool exposes map/geocoding/POI/directions actions as an LLM-compatible tool for use in agent workflows.

Supported actions:
- Geocode/search for a location
- Add marker to map
- Search for points of interest (POIs)
- Zoom to a location or POI
- (Directions/routing: not supported by Nominatim, see README)

All methods are static and results are cached for efficiency. Intended for use in LLM tool integrations and other AI Runner components.

Example usage:
    result = MapTool.search_location("Eiffel Tower, Paris")
"""

from typing import Dict, Any, Optional, List
from airunner.components.llm.managers.agent.agents.registry import ToolRegistry
import requests
import os

NOMINATIM_URL = os.getenv(
    "AIRUNNER_NOMINATIM_URL", "https://nominatim.openstreetmap.org"
)


@ToolRegistry.register("map_tool")
class MapTool:
    """LLM Tool for map/geocoding/POI actions via Nominatim/Leaflet."""

    @staticmethod
    def search_location(
        query: str, limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Geocode a location string to lat/lon using Nominatim."""
        url = f"{NOMINATIM_URL.rstrip('/')}/search"
        params = {"q": query, "format": "json", "limit": limit}
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            if results:
                return results[0] if limit == 1 else results
        except Exception:
            pass
        return None

    @staticmethod
    def search_poi(
        query: str,
        category: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: int = 1000,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for points of interest (POIs) using Nominatim's amenity/tourism queries."""
        url = f"{NOMINATIM_URL.rstrip('/')}/search"
        params = {
            "q": query,
            "format": "json",
            "limit": limit,
            "extratags": 1,
        }
        if lat and lon:
            params["viewbox"] = (
                f"{lon-radius/111320},{lat-radius/111320},{lon+radius/111320},{lat+radius/111320}"
            )
            params["bounded"] = 1
        if category:
            params["category"] = category
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    @staticmethod
    def add_marker(
        lat: float, lon: float, label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return marker data for frontend to add to map."""
        return {"lat": lat, "lon": lon, "label": label}

    @staticmethod
    def zoom_to(lat: float, lon: float, zoom: int = 13) -> Dict[str, Any]:
        """Return zoom command for frontend to center/zoom map."""
        return {"lat": lat, "lon": lon, "zoom": zoom}

    @staticmethod
    def get_directions(
        start: str, end: str, mode: str = "driving"
    ) -> Dict[str, Any]:
        """Get directions between two locations using geocoding and basic route info."""
        try:
            # Geocode start location
            start_result = MapTool.search_location(start)
            if not start_result:
                return {"error": f"Could not find start location: {start}"}

            # Geocode end location
            end_result = MapTool.search_location(end)
            if not end_result:
                return {"error": f"Could not find end location: {end}"}

            start_lat = float(start_result.get("lat", 0))
            start_lon = float(start_result.get("lon", 0))
            end_lat = float(end_result.get("lat", 0))
            end_lon = float(end_result.get("lon", 0))

            # Calculate simple distance (great circle distance)
            import math

            def haversine_distance(lat1, lon1, lat2, lon2):
                """Calculate the great circle distance between two points on Earth."""
                R = 6371  # Earth's radius in kilometers

                lat1_rad = math.radians(lat1)
                lat2_rad = math.radians(lat2)
                delta_lat = math.radians(lat2 - lat1)
                delta_lon = math.radians(lon2 - lon1)

                a = (
                    math.sin(delta_lat / 2) ** 2
                    + math.cos(lat1_rad)
                    * math.cos(lat2_rad)
                    * math.sin(delta_lon / 2) ** 2
                )
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

                return R * c

            distance_km = haversine_distance(
                start_lat, start_lon, end_lat, end_lon
            )
            distance_miles = distance_km * 0.621371

            # Create route data for frontend
            route_data = {
                "start": {
                    "name": start_result.get("display_name", start),
                    "lat": start_lat,
                    "lon": start_lon,
                },
                "end": {
                    "name": end_result.get("display_name", end),
                    "lat": end_lat,
                    "lon": end_lon,
                },
                "distance_km": round(distance_km, 2),
                "distance_miles": round(distance_miles, 2),
                "mode": mode,
                "action": "get_directions",
            }

            return route_data

        except Exception as e:
            return {"error": f"Error getting directions: {str(e)}"}

    def __call__(self, **kwargs) -> Dict[str, Any]:
        """Synchronous call interface for agent toolchains (ReAct, etc)."""
        print("MAP TOOL CALL", kwargs)
        action = kwargs.get("action")
        if not action:
            return {"error": "Missing required 'action' parameter"}

        if action == "search_location":
            return (
                self.search_location(kwargs.get("search_location", "")) or {}
            )
        if action == "get_directions":
            return (
                self.get_directions(
                    start=kwargs.get("from_location", ""),
                    end=kwargs.get("to_location", ""),
                )
                or {}
            )
        if action == "search_poi":
            return (
                self.search_poi(
                    kwargs.get("query", ""),
                    category=kwargs.get("category"),
                    lat=kwargs.get("lat"),
                    lon=kwargs.get("lon"),
                    radius=kwargs.get("radius", 1000),
                    limit=kwargs.get("limit", 10),
                )
                or {}
            )
        if action == "add_marker":
            return (
                self.add_marker(
                    kwargs.get("lat"),
                    kwargs.get("lon"),
                    label=kwargs.get("label"),
                )
                or {}
            )
        if action == "zoom_to":
            return (
                self.zoom_to(
                    kwargs.get("lat"),
                    kwargs.get("lon"),
                    zoom=kwargs.get("zoom", 13),
                )
                or {}
            )
        return {"error": f"Unknown action: {action}"}
