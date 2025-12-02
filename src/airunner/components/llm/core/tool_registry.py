"""
Decorator-based tool registration system.

This module provides a clean way to register and discover LLM tools using decorators.
Tools are automatically discovered and routed based on their metadata.
"""

from dataclasses import dataclass, field
import importlib
from typing import Callable, Dict, Optional, List, Any
from enum import Enum

from airunner.utils.application import get_logger


logger = get_logger(__name__)


class ToolCategory(Enum):
    """
    Categories for organizing tools.

    Mode-specific categories (for mode-based agent routing):
    - AUTHOR: Writing assistance, style improvement, grammar checking
    - CODE: Programming tools, code execution, debugging
    - RESEARCH: Web search, source gathering, synthesis
    - QA: Question answering, knowledge retrieval, fact checking

    Cross-mode categories (available to all modes):
    - CHAT: Conversation management
    - IMAGE: Image generation and manipulation
    - SYSTEM: Core system operations, user data, agent management
    - FILE: File operations
    - MATH: Mathematical computations
    - CONVERSATION: Conversation history and context
    - MOOD: Emotional analysis and tracking
    - ANALYSIS: General analysis tools
    - WORKFLOW: Workflow and process management
    - KNOWLEDGE: User/conversation memory and fact storage

    Legacy categories (being phased out or reorganized):
    - SEARCH: Being split into RESEARCH and QA
    - RAG: Being split into RESEARCH and QA
    - USER: Merged into SYSTEM
    """

    # Mode-specific categories (Phase 2+)
    AUTHOR = "author"  # Writing assistance mode
    CODE = "code"  # Programming assistance mode
    RESEARCH = "research"  # Research and synthesis mode
    QA = "qa"  # Question answering mode

    # Cross-mode categories (available to all modes)
    CHAT = "chat"
    IMAGE = "image"
    SYSTEM = "system"
    FILE = "file"
    MATH = "math"
    CONVERSATION = "conversation"
    MOOD = "mood"
    ANALYSIS = "analysis"
    WORKFLOW = "workflow"
    GENERATION = (
        "generation"  # Direct text generation without conversational wrappers
    )
    PROJECT = "project"  # Long-running project management
    KNOWLEDGE = "knowledge"  # User/conversation memory and fact storage

    # Legacy categories (for backward compatibility)
    SEARCH = "search"  # Use RESEARCH or QA instead
    RAG = "rag"  # Use QA or RESEARCH instead
    USER = "user"  # Use SYSTEM instead


@dataclass
class ToolInfo:
    """Metadata about a registered tool.
    
    Attributes:
        func: The tool function
        name: Unique tool identifier
        category: Tool category for organization
        description: Human-readable description
        return_direct: Whether tool returns directly to user
        requires_agent: Whether tool needs agent instance
        requires_api: Whether tool needs API access
        defer_loading: If True, tool is not loaded into initial context.
            Use search_tools to discover deferred tools on-demand.
        keywords: Additional search keywords for tool discovery
        allowed_callers: List of caller contexts that can invoke this tool.
            Empty list means callable from anywhere.
            ["code_execution"] means only callable from code sandbox.
        input_examples: Example input dicts showing proper parameter usage
    """

    func: Callable
    name: str
    category: ToolCategory
    description: str
    return_direct: bool = False
    requires_agent: bool = False
    requires_api: bool = False
    defer_loading: bool = True  # Default to deferred - use search_tools to discover
    keywords: List[str] = field(default_factory=list)
    allowed_callers: List[str] = field(default_factory=list)
    input_examples: List[Dict[str, Any]] = field(default_factory=list)


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
        defer_loading: bool = True,  # Default to deferred - use search_tools to discover
        keywords: Optional[List[str]] = None,
        allowed_callers: Optional[List[str]] = None,
        input_examples: Optional[List[Dict[str, Any]]] = None,
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
            defer_loading: If True, not loaded into initial context
            keywords: Additional search keywords for discovery
            allowed_callers: Contexts allowed to invoke this tool
            input_examples: Example input dicts for parameter guidance

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
                defer_loading=defer_loading,
                keywords=keywords or [],
                allowed_callers=allowed_callers or [],
                input_examples=input_examples or [],
            )
            cls._tools[name] = info

            if category not in cls._categories:
                cls._categories[category] = []
            
            # Remove existing entry with same name to prevent duplicates on reload
            cls._categories[category] = [
                t for t in cls._categories[category] if t.name != name
            ]
            cls._categories[category].append(info)

            return func

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[ToolInfo]:
        """Retrieve tool by name."""
        # If the requested tool name is not present, try to load default tool modules
        cls._ensure_default_tools_loaded(required_name=name)
        return cls._tools.get(name)

    @classmethod
    def get_by_category(cls, category: ToolCategory) -> List[ToolInfo]:
        """Retrieve all tools in a category."""
        cls._ensure_default_tools_loaded(required_category=category)
        return cls._categories.get(category, [])

    @classmethod
    def all(cls) -> Dict[str, ToolInfo]:
        """Retrieve all registered tools."""
        cls._ensure_default_tools_loaded()
        return dict(cls._tools)

    @classmethod
    def get_immediate_tools(cls) -> Dict[str, ToolInfo]:
        """Get tools that should be loaded immediately (defer_loading=False).
        
        These tools are always available in the initial context.
        
        Returns:
            Dict mapping tool names to ToolInfo for immediate tools
        """
        cls._ensure_default_tools_loaded()
        return {k: v for k, v in cls._tools.items() if not v.defer_loading}

    @classmethod
    def get_deferred_tools(cls) -> Dict[str, ToolInfo]:
        """Get tools that can be loaded on-demand (defer_loading=True).
        
        These tools are not included in the initial context to save tokens.
        Use search_tools to discover them when needed.
        
        Returns:
            Dict mapping tool names to ToolInfo for deferred tools
        """
        cls._ensure_default_tools_loaded()
        return {k: v for k, v in cls._tools.items() if v.defer_loading}

    @classmethod
    def clear(cls):
        """Clear all registered tools (mainly for testing)."""
        cls._tools.clear()
        cls._categories.clear()

    @classmethod
    def _ensure_default_tools_loaded(
        cls,
        required_name: Optional[str] = None,
        required_category: Optional[ToolCategory] = None,
    ) -> None:
        """Ensure that the default tools package is loaded.

        This is a defensive measure to handle test ordering where the
        registry may have been cleared by other tests. If the registry
        is currently empty, attempt to import/reload the built-in tools
        module to re-register the default tools.
        """
        try:
            # Only load defaults if specifically requested or the registry is empty.
            # This allows tests to clear the registry and run in isolation without
            # unexpectedly importing the default tools.
            should_load = False
            if required_name and required_name not in cls._tools:
                should_load = True
            if required_category and (
                required_category not in cls._categories
                or not cls._categories[required_category]
            ):
                should_load = True
            # Fallback: if no context provided, load only if registry is completely empty
            if (
                required_name is None
                and required_category is None
                and not cls._tools
            ):
                should_load = True

            if not should_load:
                return

            # Import the tools package to ensure submodules are available
            try:
                importlib.import_module("airunner.components.llm.tools")
            except Exception as exc:
                # Log failure to import the tools package for easier debugging
                logger.exception(
                    "Failed to import airunner.components.llm.tools package: %s",
                    exc,
                )
                # If we cannot import the package, stop here
                return

            # List of tool modules admitted into the package. Reload each
            # explicitly to ensure decorators run and the ToolRegistry is
            # populated even after a prior clear(). This is 'best effort'
            # and should not raise for any module import errors.
            modules_to_reload = [
                "airunner.components.llm.tools.image_tools",
                "airunner.components.llm.tools.system_tools",
                "airunner.components.llm.tools.conversation_tools",
                "airunner.components.llm.tools.math_tools",
                "airunner.components.llm.tools.reasoning_tools",
                "airunner.components.llm.tools.web_tools",
                "airunner.components.llm.tools.calendar_tools",
                "airunner.components.llm.tools.rag_tools",
                "airunner.components.llm.tools.knowledge_tools",
                "airunner.components.llm.tools.user_data_tools",
                "airunner.components.llm.tools.agent_tools",
                "airunner.components.llm.tools.mood_tools",
                "airunner.components.llm.tools.generation_tools",
                "airunner.components.llm.tools.author_tools",
                "airunner.components.llm.tools.code_tools",
                "airunner.components.llm.tools.research_tools",
                "airunner.components.llm.tools.research_document_tools",
                "airunner.components.llm.tools.research_validation_tools",
                "airunner.components.llm.tools.research_rag_tools",
                "airunner.components.llm.tools.qa_tools",
                "airunner.components.llm.tools.code_generation_tools",
                # Document editor tools for code/document editing
                "airunner.components.llm.tools.document_editor_tools",
                # Advanced tool use features
                "airunner.components.llm.tools.tool_search_tool",
                "airunner.components.llm.tools.code_execution_tool",
                # Dynamic tool creation
                "airunner.components.llm.tools.dynamic_tool_tools",
                # Workflow management tools
                "airunner.components.llm.agents.workflow_tools",
            ]
            for module_name in modules_to_reload:
                try:
                    logger.debug(
                        "Importing/reloading tool module: %s", module_name
                    )
                    mod = importlib.import_module(module_name)
                    importlib.reload(mod)
                    logger.debug(
                        "Successfully imported/reloaded: %s", module_name
                    )
                except Exception as exc:
                    # Best effort - don't fail if specific tool module isn't
                    # present or throws during import, but log the exception
                    logger.exception(
                        "Failed to import/reload tool module %s: %s",
                        module_name,
                        exc,
                    )
                    continue
        except Exception:
            # Guard against any unexpected exception while ensuring defaults
            pass


def tool(
    name: str,
    category: ToolCategory,
    description: str,
    return_direct: bool = False,
    requires_agent: bool = False,
    requires_api: bool = False,
    defer_loading: bool = True,  # Default to deferred - use search_tools to discover
    keywords: Optional[List[str]] = None,
    allowed_callers: Optional[List[str]] = None,
    input_examples: Optional[List[Dict[str, Any]]] = None,
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
            keywords=["picture", "art", "create"],
            input_examples=[
                {"prompt": "A sunset over mountains", "width": 512, "height": 512},
            ],
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
        defer_loading: If True, not in initial context (use search_tools)
        keywords: Additional search keywords for discovery
        allowed_callers: Contexts allowed to invoke this tool
        input_examples: Example input dicts for parameter guidance

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
        defer_loading=defer_loading,
        keywords=keywords,
        allowed_callers=allowed_callers,
        input_examples=input_examples,
    )
