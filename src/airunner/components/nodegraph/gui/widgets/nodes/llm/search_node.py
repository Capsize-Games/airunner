"""
SearchNode: NodeGraphQt node for performing aggregated search queries.

This node interfaces with AggregatedSearchTool to provide search results as node outputs.
"""

from airunner.components.nodegraph.gui.widgets.nodes.llm.base_llm_node import (
    BaseLLMNode,
)
import asyncio

from airunner.components.tools.search_tool import AggregatedSearchTool


class SearchNode(BaseLLMNode):
    """Node for performing aggregated search queries using AggregatedSearchTool."""

    __identifier__ = "llm"
    NODE_NAME = "Aggregated Search"

    def __init__(self):
        super().__init__()
        self.add_text_input("query", "Query", default="")
        self.add_combo_input(
            "category",
            "Category",
            items=["all", "web", "academic", "news", "code", "books", "q&a"],
            default="all",
        )
        self.add_output("results", "Results")

    def run_node(self, **kwargs) -> None:
        query = self.get_property("query")
        category = self.get_property("category")
        if not query:
            self.set_output_val("results", [])
            return
        # Run the async search in a blocking way for node execution
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            AggregatedSearchTool.aggregated_search(query, category)
        )
        self.set_output_val("results", results)
