"""
WeatherTool: Provides current weather information for a given location using the agent's weather search libraries.
"""

from typing import Any, Optional
from llama_index.core.tools.types import ToolMetadata, ToolOutput
from airunner.handlers.llm.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)


class WeatherTool(BaseConversationEngine):
    """Tool for retrieving current weather information."""

    def __init__(
        self,
        agent: Any,
        metadata: ToolMetadata,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(agent)
        self._metadata = metadata
        self.agent = agent

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    def call(
        self, location: Optional[str] = None, **kwargs: Any
    ) -> ToolOutput:
        # Use the agent's weather search capability (assume agent has weather_mixin)
        if not location:
            location = kwargs.get("input")
        if not location:
            location = "current location"
        # This should call the agent's weather search logic
        weather_info = self.agent.get_weather_info(location)
        return ToolOutput(
            content=weather_info,
            tool_name=self.metadata.name,
            raw_input={"location": location},
            raw_output=weather_info,
        )

    @classmethod
    def from_defaults(
        cls,
        agent: Any,
        name: str = "weather_tool",
        description: str = "Get current weather information for a location.",
    ) -> "WeatherTool":
        metadata = ToolMetadata(
            name=name,
            description=description,
            return_direct=False,
        )
        return cls(agent=agent, metadata=metadata)
