"""
MapToolsMixin: Mixin for providing map/geocoding/POI capabilities to LLM agents using MapTool.

Exposes a `map_tool` property for use in agent toolchains.
"""

from typing import Annotated, Optional, Literal, Dict, Any
from airunner.components.llm.managers.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)
from airunner.components.llm.managers.agent.tools.map_tool import MapTool
from llama_index.core.tools import FunctionTool


class MapToolsMixin(ToolSingletonMixin):
    """Provides a map tool interface for LLM agents."""

    @property
    def map_tool(self):
        """
        Return a FunctionTool wrapper around MapTool for agent toolchains.
        Enables the ReAct agent to call MapTool methods via the __call__ interface.
        """

        def map_tool_func(**kwargs) -> Dict[str, Any]:
            """Execute map tool actions via MapTool.__call__ interface."""
            tool_instance = MapTool()
            return tool_instance(**kwargs)

        return self._get_or_create_singleton(
            "_map_tool",
            FunctionTool.from_defaults,
            map_tool_func,
            name="map_tool",
            description="Perform map/geocoding/POI/directions actions using Nominatim/Leaflet.",
            return_direct=True,
        )
