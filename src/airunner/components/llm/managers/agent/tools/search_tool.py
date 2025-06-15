"""
AggregatedSearchTool LLM Tool Integration

This tool exposes the AggregatedSearchTool as an LLM-compatible tool for use in agent workflows.
"""

from typing import Dict, List
from airunner.components.llm.managers.agent.agents.registry import ToolRegistry
from airunner.components.tools.search_tool import AggregatedSearchTool


@ToolRegistry.register("search")
class SearchTool:
    """LLM Tool wrapper for AggregatedSearchTool."""

    @staticmethod
    async def search(
        query: str, category: str = "all"
    ) -> Dict[str, List[dict]]:
        """Perform an aggregated search using the static AggregatedSearchTool.

        Args:
            query (str): The search query string.
            category (str): The service category (web, academic, news, code, books, q&a, or 'all').

        Returns:
            Dict[str, List[dict]]: Mapping of service name to list of result dicts.
        """
        return await AggregatedSearchTool.aggregated_search(query, category)

    @staticmethod
    def search_sync(
        query: str, category: str = "all"
    ) -> Dict[str, List[dict]]:
        """Synchronous wrapper for LLM tool compatibility."""
        return AggregatedSearchTool.aggregated_search_sync(query, category)

    def __call__(
        self, query: str, category: str = "all", **kwargs
    ) -> Dict[str, List[dict]]:
        """Synchronous call interface for agent toolchains (ReAct, etc)."""
        return self.search_sync(query, category)
