"""
RespondToSearchQueryTool: Takes raw search results and an original user query,
then uses an LLM to synthesize a natural language response.
"""

from typing import Any, List, Dict, Union, Optional
from llama_index.core.tools import ToolMetadata, BaseTool

from airunner.handlers.llm.agent.agents.registry import ToolRegistry
from airunner.handlers.llm.agent.chat_engine import (
    RefreshSimpleChatEngine,
)

import logging
import json

logger = logging.getLogger(__name__)


@ToolRegistry.register("respond_to_search_query")
class RespondToSearchQueryTool(BaseTool):  # MODIFIED base class
    """Tool for synthesizing a response from search results and an original query.

    Args (for __call__):
        search_results (Union[str, Dict[str, List[Dict[str, Any]]]]): Raw search results.
        original_query (str): The original user query that led to these search results.
    Returns (from __call__):
        str: A natural language response synthesized from the search results.
    """

    name = "respond_to_search_query"
    description = (
        "Synthesizes a natural language answer based on provided search results "
        "and the user's original query. Use this tool after a search has been performed."
    )
    _agent: Any
    _synthesis_engine: Optional[RefreshSimpleChatEngine] = None

    def __init__(self, agent: Any):  # MODIFIED signature
        super().__init__()  # MODIFIED super call
        self._agent = agent
        # self._synthesis_engine is lazy-loaded

    @property
    def metadata(self) -> ToolMetadata:
        """Tool metadata."""
        return ToolMetadata(
            name=self.name,
            description=self.description,
            # fn_schema is not strictly needed here as FunctionTool infers it,
            # but could be added for more direct LlamaIndex agent compatibility.
        )

    def _get_synthesis_engine(self) -> RefreshSimpleChatEngine:
        if self._synthesis_engine is None:
            if (
                not self._agent
                or not hasattr(self._agent, "llm")
                or not self._agent.llm
            ):
                raise ValueError(
                    "RespondToSearchQueryTool requires an agent with a configured LLM for synthesis."
                )

            system_prompt = (
                "You are an AI assistant. Based on the following search results and the user's original query, "
                "provide a comprehensive and informative answer to the user's query. "
                "Cite information from the search results where appropriate, but present the answer in your own words. "
                "If the search results are not relevant or sufficient, state that you couldn't find a good answer."
                "Do not refer to 'the search results' directly in your answer, just use the information they contain."
            )
            self._synthesis_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=system_prompt,
                llm=self._agent.llm,
                memory=None,  # This tool is stateless for synthesis
            )
        return self._synthesis_engine

    def __call__(  # This method is wrapped by FunctionTool
        self,
        search_results: Union[str, Dict[str, List[Dict[str, Any]]]],
        original_query: str,
    ) -> str:
        logger.debug(
            f"RespondToSearchQueryTool called with original_query: '{original_query}' and search_results type: {type(search_results)}"
        )

        if isinstance(search_results, str):
            try:
                search_results = json.loads(search_results)
            except json.JSONDecodeError:
                logger.warning(
                    "search_results was a string but not valid JSON. Treating as plain text."
                )
                # Fallback: if it's a string but not JSON, maybe it's pre-formatted.
                # Or, it could be an error message.
                # For now, we'll just pass it through, but this might need refinement.

        # Format search results into a string for the LLM prompt
        formatted_results_str = ""
        if isinstance(search_results, dict):
            for service, items in search_results.items():
                if isinstance(items, list):
                    formatted_results_str += f"Results from {service}:\n"
                    for item in items[:5]:  # Limit to top 5 results per service
                        title = item.get("title", "N/A")
                        snippet = item.get("snippet", "No snippet available.")
                        link = item.get("link", "")
                        formatted_results_str += f"- Title: {title}\n  Snippet: {snippet}\n  Source: {link}\n"
                    formatted_results_str += "\n"
        elif isinstance(search_results, str):  # If it was a non-JSON string
            formatted_results_str = search_results
        else:
            formatted_results_str = "No usable search results provided."
            logger.warning(
                "Search results were not a dict or string. Cannot format for LLM."
            )

        synthesis_prompt = (
            f"User's original query: '{original_query}'\n\n"
            f"Relevant information found:\n{formatted_results_str}\n\n"
            "Please provide a comprehensive answer to the user's original query based on this information:"
        )

        try:
            engine = self._get_synthesis_engine()
            # Using chat method for a single turn with the synthesis engine
            response = engine.chat(synthesis_prompt)
            final_answer = (
                response.response if hasattr(response, "response") else str(response)
            )
            logger.debug(f"Synthesized response: {final_answer}")
            return final_answer
        except Exception as e:
            logger.error(f"Error during synthesis in RespondToSearchQueryTool: {e}")
            return "I encountered an error while trying to process the search results."

    # Required by BaseTool
    def call(
        self,
        search_results: Union[str, Dict[str, List[Dict[str, Any]]]],
        original_query: str,
        **kwargs: Any,
    ) -> str:
        """Execute the tool."""
        return self.__call__(
            search_results=search_results, original_query=original_query
        )

    # Required by BaseTool
    async def acall(
        self,
        search_results: Union[str, Dict[str, List[Dict[str, Any]]]],
        original_query: str,
        **kwargs: Any,
    ) -> str:
        """Execute the tool asynchronously."""
        # For now, run the synchronous version.
        # TODO: Implement true async execution if RefreshSimpleChatEngine supports achat.
        return self.call(
            search_results=search_results,
            original_query=original_query,
            **kwargs,
        )


# Ensure this tool is also available via the mixin
