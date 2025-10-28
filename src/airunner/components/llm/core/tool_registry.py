"""
Decorator-based tool registration system.

This module provides a clean way to register and discover LLM tools using decorators.
Tools are automatically discovered and routed based on their metadata.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional, List
from enum import Enum


class ToolCategory(Enum):
    """Categories for organizing tools."""

    CHAT = "chat"
    IMAGE = "image"
    SYSTEM = "system"
    FILE = "file"
    SEARCH = "search"
    USER = "user"
    CONVERSATION = "conversation"
    RAG = "rag"
    MOOD = "mood"
    ANALYSIS = "analysis"
    WORKFLOW = "workflow"


@dataclass
class ToolInfo:
    """Metadata about a registered tool."""

    func: Callable
    name: str
    category: ToolCategory
    description: str
    return_direct: bool = False
    requires_agent: bool = False
    requires_api: bool = False


class ToolRegistry:
    """
    Central registry for LLM tools.

    Maintains a mapping of tool names to their metadata and provides
    methods for discovering and retrieving tools by category or name.
    """

    _tools: Dict[str, ToolInfo] = {}
    _categories: Dict[ToolCategory, List[ToolInfo]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        category: ToolCategory,
        description: str,
        return_direct: bool = False,
        requires_agent: bool = False,
        requires_api: bool = False,
    ) -> Callable:
        """
        Register a tool with metadata.

        Args:
            name: Unique tool identifier
            category: Tool category for organization
            description: Human-readable description of tool purpose
            return_direct: Whether tool returns directly to user
            requires_agent: Whether tool needs agent instance
            requires_api: Whether tool needs API access

        Returns:
            Decorator function that registers the tool
        """

        def decorator(func: Callable) -> Callable:
            info = ToolInfo(
                func=func,
                name=name,
                category=category,
                description=description,
                return_direct=return_direct,
                requires_agent=requires_agent,
                requires_api=requires_api,
            )
            cls._tools[name] = info

            if category not in cls._categories:
                cls._categories[category] = []
            cls._categories[category].append(info)

            return func

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[ToolInfo]:
        """Retrieve tool by name."""
        return cls._tools.get(name)

    @classmethod
    def get_by_category(cls, category: ToolCategory) -> List[ToolInfo]:
        """Retrieve all tools in a category."""
        return cls._categories.get(category, [])

    @classmethod
    def all(cls) -> Dict[str, ToolInfo]:
        """Retrieve all registered tools."""
        return dict(cls._tools)

    @classmethod
    def clear(cls):
        """Clear all registered tools (mainly for testing)."""
        cls._tools.clear()
        cls._categories.clear()


def tool(
    name: str,
    category: ToolCategory,
    description: str,
    return_direct: bool = False,
    requires_agent: bool = False,
    requires_api: bool = False,
) -> Callable:
    """
    Decorator to register an LLM tool.

    Example:
        @tool(
            name="generate_image",
            category=ToolCategory.IMAGE,
            description="Generate an image from a text prompt",
            return_direct=True,
            requires_api=True,
        )
        def generate_image(prompt: str, width: int, height: int) -> str:
            # Implementation
            return "Image generated"

    Args:
        name: Unique tool identifier
        category: Tool category
        description: Tool description
        return_direct: Whether to return result directly
        requires_agent: Whether tool needs agent instance
        requires_api: Whether tool needs API access

    Returns:
        Registered function
    """
    return ToolRegistry.register(
        name=name,
        category=category,
        description=description,
        return_direct=return_direct,
        requires_agent=requires_agent,
        requires_api=requires_api,
    )
