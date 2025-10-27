"""
Central module for loading all LLM tools.

Import this module to register all available tools with the ToolRegistry.
"""

# Import all tool modules to trigger registration
from airunner.components.llm.tools import (
    image_tools,
    system_tools,
    conversation_tools,
)
from airunner.components.calendar.tools import calendar_tools

__all__ = [
    "image_tools",
    "system_tools",
    "conversation_tools",
    "calendar_tools",
]
