"""
SearchEngineTool: A tool for performing internet searches and synthesizing responses.

This tool follows the same pattern as ChatEngineTool, providing a clean interface
for search functionality with proper streaming response handling.
"""

from typing import Any, Optional, Dict, List, Union
import logging
import json

from llama_index.core.tools.types import (
    AsyncBaseTool,
    ToolMetadata,
    ToolOutput,
)

from airunner.handlers.llm.agent.chat_engine import RefreshSimpleChatEngine
from airunner.tools.search_tool import AggregatedSearchTool
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.utils.application.mediator_mixin import MediatorMixin

logger = logging.getLogger(__name__)


class SearchEngineTool(AsyncBaseTool, SettingsMixin, MediatorMixin):
    """Search tool.

    A tool for performing internet searches and synthesizing natural language responses.
    This tool internally handles the two-step process:
    1. Perform search using AggregatedSearchTool
    2. Synthesize response using an LLM
    """

    def __init__(
        self,
        llm: Any,
        metadata: ToolMetadata,
        resolve_input_errors: bool = True,
        agent: Any = None,
        do_handle_response: bool = True,
        *args: Any,
        **kwargs: Any,
    ):
        self.do_handle_response: bool = do_handle_response
        self.llm = llm
        if not llm:
            raise ValueError("LLM must be provided for search synthesis.")
        self._metadata = metadata
        self._resolve_input_errors = resolve_input_errors
        self.agent = agent
        self._do_interrupt: bool = False
        self._synthesis_engine: Optional[RefreshSimpleChatEngine] = None
        super().__init__(*args, **kwargs)

    @classmethod
    def from_defaults(
        cls,
        llm: Any,
        name: Optional[str] = None,
        description: Optional[str] = None,
        return_direct: bool = True,  # Default to True for final responses
        resolve_input_errors: bool = True,
        agent: Any = None,
        do_handle_response: bool = True,
    ) -> "SearchEngineTool":
        name = name or "search_engine_tool"
        description = description or (
            "Performs an internet search for a given query and returns a comprehensive, "
            "natural language answer based on the search results. Use this tool when you need "
            "to find current information from the internet."
        )

        metadata = ToolMetadata(
            name=name, description=description, return_direct=return_direct
        )
        return cls(
            llm=llm,
            metadata=metadata,
            resolve_input_errors=resolve_input_errors,
            agent=agent,
            do_handle_response=do_handle_response,
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    def _get_synthesis_engine(self) -> RefreshSimpleChatEngine:
        """Lazy-load the synthesis engine for generating responses from search results."""
        if self._synthesis_engine is None:
            system_prompt = (
                "You are an AI assistant. Based on the following search results and the user's original query, "
                "provide a comprehensive and informative answer to the user's query. "
                "Cite information from the search results where appropriate, but present the answer in your own words. "
                "If the search results are not relevant or sufficient, state that you couldn't find a good answer. "
                "Do not refer to 'the search results' directly in your answer, just use the information they contain."
            )
            self._synthesis_engine = RefreshSimpleChatEngine.from_defaults(
                system_prompt=system_prompt,
                llm=self.llm,
                memory=None,  # This tool is stateless for synthesis
            )
        return self._synthesis_engine

    def _format_search_results(
        self, search_results: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Format search results into a string for the LLM prompt."""
        formatted_results_str = ""
        if isinstance(search_results, dict):
            for service, items in search_results.items():
                if isinstance(items, list):
                    formatted_results_str += f"Results from {service}:\n"
                    for item in items[
                        :5
                    ]:  # Limit to top 5 results per service
                        title = item.get("title", "N/A")
                        snippet = item.get("snippet", "No snippet available.")
                        link = item.get("link", "")
                        formatted_results_str += f"- Title: {title}\n  Snippet: {snippet}\n  Source: {link}\n"
                    formatted_results_str += "\n"
        else:
            formatted_results_str = "No usable search results provided."
            logger.warning(
                "Search results were not a dict. Cannot format for LLM."
            )
        return formatted_results_str

    def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
        query_str = self._get_query_str(*args, **kwargs)
        llm_request = kwargs.get("llm_request", LLMRequest.from_default())

        # Set up LLM request if needed
        if hasattr(self.llm, "llm_request"):
            self.llm.llm_request = llm_request

        response = ""

        if not self._do_interrupt:
            do_not_display = kwargs.get("do_not_display", False)
            category = kwargs.get("category", "all")

            try:
                # Step 1: Perform the search
                logger.info(
                    f"SearchEngineTool: Performing search for query: '{query_str}'"
                )
                search_results = AggregatedSearchTool.aggregated_search_sync(
                    query_str, category
                )

                if not search_results or not isinstance(search_results, dict):
                    logger.warning("Search returned no valid results")
                    response = (
                        "I couldn't find relevant information for your query."
                    )
                else:
                    # Step 2: Format search results
                    formatted_results = self._format_search_results(
                        search_results
                    )

                    # Step 3: Synthesize response using LLM
                    synthesis_prompt = (
                        f"User's original query: '{query_str}'\n\n"
                        f"Relevant information found:\n{formatted_results}\n\n"
                        "Please provide a comprehensive answer to the user's original query based on this information:"
                    )

                    logger.info(
                        "SearchEngineTool: Synthesizing response from search results"
                    )
                    synthesis_engine = self._get_synthesis_engine()
                    streaming_response = synthesis_engine.stream_chat(
                        synthesis_prompt
                    )

                    # Step 4: Handle streaming response like ChatEngineTool
                    is_first_message = True
                    try:
                        for token in streaming_response.response_gen:
                            if self._do_interrupt:
                                break
                            if not token:
                                continue  # Skip empty tokens
                            response += token
                            if (
                                response != "Empty Response"
                                and self.do_handle_response
                                and self.agent
                            ):
                                # Pass the individual token, not the accumulated response
                                self.agent.handle_response(
                                    token,
                                    is_first_message,
                                    do_not_display=do_not_display,
                                    do_tts_reply=llm_request.do_tts_reply,
                                )
                            is_first_message = False
                    except Exception as e:
                        logger.error(f"Error during response streaming: {e}")
                        response = "I encountered an error while processing the search results."

            except Exception as e:
                logger.error(f"Error in SearchEngineTool: {e}", exc_info=True)
                response = "I encountered an error while trying to search for information."

        self._do_interrupt = False

        return ToolOutput(
            content=str(response),
            tool_name=self.metadata.name,
            raw_input={"input": query_str},
            raw_output=response,
        )

    async def acall(self, *args, **kwargs):
        """Async version - for now, just call the sync version."""
        return self.call(*args, **kwargs)

    def _get_query_str(self, *args: Any, **kwargs: Any) -> str:
        """Extract query string from arguments - same pattern as ChatEngineTool."""
        if args is not None and len(args) > 0:
            query_str = str(args[0])
        elif kwargs is not None and "input" in kwargs:
            # NOTE: this assumes our default function schema of `input`
            query_str = kwargs["input"]
        elif kwargs is not None and self._resolve_input_errors:
            query_str = str(kwargs)
        else:
            raise ValueError(
                "Cannot call search engine without specifying `input` parameter."
            )
        return query_str
