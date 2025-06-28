"""
MapToolsMixin: Mixin for providing map/geocoding/POI capabilities to LLM agents using MapTool.

Exposes a `map_tool` property for use in agent toolchains.
"""

from typing import Annotated, Optional, Literal
from airunner.components.llm.managers.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)
from airunner.components.llm.managers.agent.tools.map_tool import MapTool


class MapToolsMixin(ToolSingletonMixin):
    """Provides a map tool interface for LLM agents."""

    @property
    def map_tool(self):
        """
        Return a singleton instance of the real MapTool (not a FunctionTool) for agent toolchains.
        Ensures the ReAct agent can call the actual MapTool implementation.
        """
        if not hasattr(self, "_map_tool_instance"):
            self._map_tool_instance = MapTool.from_defaults(
                llm=getattr(self, "llm", None),
                agent=self,
                name="map_tool",
                description="Perform map/geocoding/POI/directions actions using Nominatim/Leaflet.",
                return_direct=True,
            )
        return self._map_tool_instance
