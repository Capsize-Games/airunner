"""
Central module for loading all LLM tools.

Import this module to register all available tools with the ToolRegistry.
"""

# Import all tool modules to trigger registration
from airunner.components.llm.tools import (
    image_tools,
    system_tools,
    conversation_tools,
    math_tools,
    reasoning_tools,
    web_tools,
    calendar_tools,
    rag_tools,
    knowledge_tools,
    user_data_tools,
    agent_tools,
    # Phase 2: Mode-specific tools
    author_tools,
    code_tools,
    research_tools,
    qa_tools,
)
from airunner.components.calendar.tools import (
    calendar_tools as langchain_calendar_tools,
)

__all__ = [
    "image_tools",
    "system_tools",
    "conversation_tools",
    "math_tools",
    "reasoning_tools",
    "web_tools",
    "calendar_tools",
    "rag_tools",
    "knowledge_tools",
    "user_data_tools",
    "agent_tools",
    "langchain_calendar_tools",
    # Phase 2: Mode-specific tools
    "author_tools",
    "code_tools",
    "research_tools",
    "qa_tools",
]
