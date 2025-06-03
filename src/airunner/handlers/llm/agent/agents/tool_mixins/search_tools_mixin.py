"""
SearchToolsMixin: Mixin for providing search capabilities to LLM agents using AggregatedSearchTool.

Exposes a `search` method for use in agent toolchains.
"""

from airunner.handlers.llm.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)
from airunner.tools.search_tool import AggregatedSearchTool
from llama_index.core.tools import FunctionTool
from typing import Dict, List


class SearchToolsMixin(ToolSingletonMixin):
    """Provides a search tool interface for LLM agents."""

    async def search(self, query: str, category: str = "all") -> Dict[str, List[dict]]:
        """Perform an internet search for a given query and category.

        Args:
            query (str): The search query string.
            category (str): The service category (web, academic, news, code, books, q&a, or 'all').

        Returns:
            Dict[str, List[dict]]: Mapping of service name to list of result dicts.
        """
        return await AggregatedSearchTool.aggregated_search(query, category)

    @property
    def search_tool(self):
        def search_sync(query: str, category: str = "all") -> Dict[str, List[dict]]:
            """Perform an internet search for a given query and category.

            Args:
                query (str): The search query string.
                category (str): The service category (web, academic, news, code, books, q&a, or 'all').

            Returns:
                Dict[str, List[dict]]: Mapping of service name to list of result dicts.
            """
            import asyncio

            try:
                # Try to get a running event loop (works in main thread/async context)
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running event loop in this thread: safe to use asyncio.run()
                return AggregatedSearchTool.aggregated_search_sync(query, category)
            else:
                # There is a running event loop (main thread or async context)
                # Use run_until_complete if not already running
                if loop.is_running():
                    # In a running event loop (e.g., Jupyter, async context):
                    # This is not safe to block, so raise or return error
                    raise RuntimeError(
                        "Cannot run blocking search in a running event loop. Use the async 'search' method instead."
                    )
                else:
                    return loop.run_until_complete(
                        AggregatedSearchTool.aggregated_search(query, category)
                    )

        # Ensure the FunctionTool has the correct name for tool_choice matching
        return self._get_or_create_singleton(
            "_search_tool",
            FunctionTool.from_defaults,
            search_sync,
            name="search_tool",
            description="Perform an internet search for a given query and category.",
            return_direct=True,
        )
