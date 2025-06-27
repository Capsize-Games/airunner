"""
MapTool: LLM Tool Integration for Map/Nominatim/Leaflet Actions

This tool exposes map/geocoding/POI/directions actions as an LLM-compatible tool for use in agent workflows.

Supported actions:
- Geocode/search for a location
- Add marker to map
- Search for points of interest (POIs)
- Zoom to a location or POI
- Get directions between two locations

All methods are static and results are cached for efficiency. Intended for use in LLM tool integrations and other AI Runner components.

Example usage:
    result = MapTool.search_location("Eiffel Tower, Paris")
"""

import asyncio
import math
import os
import requests
from typing import Any, Dict, List, Optional

from llama_index.core.tools.types import (
    ToolMetadata,
    ToolOutput,
)

from airunner.components.llm.managers.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)

NOMINATIM_URL = os.getenv("AIRUNNER_NOMINATIM_URL", "http://localhost:8080")


class MapTool(BaseConversationEngine):
    """Tool for map/geocoding/POI actions via Nominatim/Leaflet."""

    def __init__(
        self,
        agent: Any,
        llm: Any,
        metadata: ToolMetadata,
        resolve_input_errors: bool = True,
        do_handle_response: bool = True,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(agent)
        self.do_handle_response: bool = do_handle_response
        self.llm = llm
        if not llm:
            raise ValueError("MapTool requires an LLM instance.")
        self._metadata = metadata
        self._resolve_input_errors = resolve_input_errors
        self.agent = agent
        self._do_interrupt: bool = False
        self._logger = kwargs.pop("logger", None)
        if self._logger is None:
            import logging

            self._logger = logging.getLogger(__name__)

    @property
    def logger(self):
        return self._logger

    @classmethod
    def from_defaults(
        cls,
        llm: Any,
        name: Optional[str] = None,
        description: Optional[str] = None,
        return_direct: bool = True,
        resolve_input_errors: bool = True,
        agent: Any = None,
        do_handle_response: bool = True,
    ) -> "MapTool":
        metadata = ToolMetadata(
            name=name or "map_tool",
            description=description
            or "Tool for map/geocoding/POI/directions actions using Nominatim/Leaflet.",
            return_direct=return_direct,
        )
        return cls(
            agent=agent,
            llm=llm,
            metadata=metadata,
            resolve_input_errors=resolve_input_errors,
            do_handle_response=do_handle_response,
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    @staticmethod
    def search_location(
        query: str, limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Geocode a location string to lat/lon using Nominatim."""
        # Try multiple endpoints for reliability
        endpoints = [
            os.getenv("AIRUNNER_NOMINATIM_URL", "http://localhost:8080"),
            "http://localhost:8080",  # Local server
            "https://nominatim.openstreetmap.org",  # Fallback to public
        ]

        for base_url in endpoints:
            url = f"{base_url.rstrip('/')}/search"
            params = {"q": query, "format": "json", "limit": limit}
            try:
                resp = requests.get(url, params=params, timeout=5)
                resp.raise_for_status()
                results = resp.json()
                if results:
                    return results[0] if limit == 1 else results
            except Exception as e:
                print(f"Failed to query {base_url}: {e}")
                continue
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

    def __call__(self, **kwargs) -> ToolOutput:
        """Synchronous call interface for agent toolchains (ReAct, etc)."""
        return self.call(**kwargs)

    def call(
        self, *args: Any, tool_call: bool = False, **kwargs: Any
    ) -> ToolOutput:
        """Main call method that returns ToolOutput."""
        self.logger.info(
            "Running MapTool with args: %s, kwargs: %s", args, kwargs
        )

        action = kwargs.get("action")
        if not action:
            error_msg = "Missing required 'action' parameter"
            return ToolOutput(
                content=error_msg,
                tool_name=self.metadata.name,
                raw_input=kwargs,
                raw_output={"error": error_msg},
            )

        try:
            result = None
            if action == "search_location":
                result = self.search_location(
                    kwargs.get("search_location", "")
                )
            elif action == "get_directions":
                result = self.get_directions(
                    start=kwargs.get("from_location", ""),
                    end=kwargs.get("to_location", ""),
                )
            elif action == "search_poi":
                result = self.search_poi(
                    kwargs.get("poi_query", ""),
                    category=kwargs.get("category"),
                    lat=kwargs.get("lat"),
                    lon=kwargs.get("lon"),
                    radius=kwargs.get("radius", 1000),
                    limit=kwargs.get("limit", 10),
                )
            elif action == "add_marker":
                result = self.add_marker(
                    kwargs.get("lat"),
                    kwargs.get("lon"),
                    label=kwargs.get("label"),
                )
            elif action == "zoom_to":
                result = self.zoom_to(
                    kwargs.get("lat"),
                    kwargs.get("lon"),
                    zoom=kwargs.get("zoom", 13),
                )
            else:
                error_msg = f"Unknown action: {action}"
                return ToolOutput(
                    content=error_msg,
                    tool_name=self.metadata.name,
                    raw_input=kwargs,
                    raw_output={"error": error_msg},
                )

            # Note: Map results are sent to frontend via MAP_SEARCH_RESULT_SIGNAL from LLMGenerateWorker
            # The raw_output contains the actual map data that the frontend will process

            # Create user-friendly content message with the actual data
            if (
                action == "get_directions"
                and "start" in result
                and "end" in result
            ):
                content = (
                    f"Found directions from {result['start']['name']} to {result['end']['name']}. "
                    f"Distance: {result['distance_miles']} miles ({result['distance_km']} km). "
                    f"Route data sent to map."
                )
            elif action == "search_location" and result:
                if isinstance(result, list):
                    content = f"Found {len(result)} location(s). Results sent to map."
                else:
                    content = f"Found location: {result.get('display_name', 'Unknown')}. Marker sent to map."
            elif "error" in result:
                content = f"Map error: {result['error']}"
            else:
                content = f"Map action '{action}' completed successfully"

            return ToolOutput(
                content=content,
                tool_name=self.metadata.name,
                raw_input=kwargs,
                raw_output=result,
            )

        except Exception as e:
            error_msg = f"Error performing map action '{action}': {str(e)}"
            self.logger.error(error_msg)
            return ToolOutput(
                content=error_msg,
                tool_name=self.metadata.name,
                raw_input=kwargs,
                raw_output={"error": str(e)},
            )

    async def acall(self, *args, **kwargs):
        """Async version of call (for future use)."""
        return await asyncio.to_thread(self.call, *args, **kwargs)
