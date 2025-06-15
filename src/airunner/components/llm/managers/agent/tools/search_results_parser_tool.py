"""
RespondToSearchQueryTool: Takes raw search results and an original user query,
then uses an LLM to synthesize a natural language response.
"""

from typing import Any

from airunner.components.llm.managers.agent.agents.registry import ToolRegistry
from airunner.components.llm.managers.agent.tools.search_engine_tool import (
    SearchEngineTool,
)

import logging

logger = logging.getLogger(__name__)


# DEPRECATED: Use SearchEngineTool.synthesize_from_search_results instead.
@ToolRegistry.register("respond_to_search_query")
class RespondToSearchQueryTool:
    """[DEPRECATED] Use SearchEngineTool.synthesize_from_search_results instead."""

    def __init__(self, agent: Any):
        self.agent = agent

    def __call__(self, search_results, original_query):
        return SearchEngineTool.synthesize_from_search_results(
            self.agent, search_results, original_query
        )

    def call(self, search_results, original_query, **kwargs):
        return self.__call__(search_results, original_query)

    async def acall(self, search_results, original_query, **kwargs):
        return self.call(search_results, original_query, **kwargs)


# Ensure this tool is also available via the mixin
