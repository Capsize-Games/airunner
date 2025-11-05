"""
Tool executor for running LLM tools with proper context injection.

Handles the execution of tools with automatic dependency injection
of agent, API, and other required context.
"""

import logging
from typing import Any, Optional, Callable
from llama_index.core.tools import FunctionTool

from airunner.components.llm.core.tool_registry import ToolRegistry, ToolInfo


class ToolExecutor:
    """
    Executes LLM tools with automatic dependency injection.

    Wraps tool functions with proper context (agent, API) and converts
    them to llama_index FunctionTool instances.
    """

    def __init__(
        self,
        agent: Optional[Any] = None,
        api: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize tool executor.

        Args:
            agent: Agent instance for tools that require it
            api: API instance for tools that require it
            logger: Logger instance
        """
        self.agent = agent
        self.api = api
        self.logger = logger or logging.getLogger(__name__)

    def wrap_tool(self, tool_info: ToolInfo) -> Callable:
        """
        Wrap a tool function with dependency injection.

        Args:
            tool_info: Tool metadata

        Returns:
            Wrapped function with dependencies injected
        """

        def wrapped(*args, **kwargs):
            # Inject dependencies if required
            if tool_info.requires_agent and self.agent:
                kwargs["agent"] = self.agent
            if tool_info.requires_api and self.api:
                kwargs["api"] = self.api

            try:
                return tool_info.func(*args, **kwargs)
            except Exception as e:
                self.logger.error(
                    f"Error executing tool {tool_info.name}: {e}",
                    exc_info=True,
                )
                return f"Error: {str(e)}"

        return wrapped

    def to_function_tool(self, tool_info: ToolInfo) -> FunctionTool:
        """
        Convert tool to llama_index FunctionTool.

        Args:
            tool_info: Tool metadata

        Returns:
            Configured FunctionTool instance
        """
        wrapped = self.wrap_tool(tool_info)

        return FunctionTool.from_defaults(
            fn=wrapped,
            name=tool_info.name,
            description=tool_info.description,
            return_direct=tool_info.return_direct,
        )

    def get_all_tools(
        self,
        categories: Optional[list] = None,
    ) -> list[FunctionTool]:
        """
        Get all tools as FunctionTool instances.

        Args:
            categories: Filter by specific categories

        Returns:
            List of configured FunctionTool instances
        """
        tools = []

        for tool_info in ToolRegistry.all().values():
            # Filter by category if specified
            if categories and tool_info.category not in categories:
                continue

            # Check dependencies
            if tool_info.requires_agent and not self.agent:
                self.logger.warning(
                    f"Skipping tool {tool_info.name}: requires agent"
                )
                continue

            if tool_info.requires_api and not self.api:
                self.logger.warning(
                    f"Skipping tool {tool_info.name}: requires API"
                )
                continue

            tools.append(self.to_function_tool(tool_info))

        return tools
