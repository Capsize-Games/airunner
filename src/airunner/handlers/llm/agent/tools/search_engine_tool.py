import time
from typing import Any, Optional, Dict, List

from llama_index.core.tools.types import (
    ToolMetadata,
    ToolOutput,
)

from airunner.handlers.llm.agent.chat_engine import RefreshSimpleChatEngine
from airunner.tools.search_tool import AggregatedSearchTool
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.agent.engines.base_conversation_engine import (
    BaseConversationEngine,
)


class SearchEngineTool(BaseConversationEngine):
    """Search tool.

    A tool for performing internet searches and synthesizing natural language responses.
    This tool is context-aware: it uses and updates the ongoing chat history/memory, enabling follow-up queries to be answered in a conversational, contextually relevant way (like ChatEngineTool).
    This tool internally handles the two-step process:
    1. Perform search using AggregatedSearchTool
    2. Synthesize response using an LLM, with full conversational context
    """

    def __init__(
        self,
        agent: Any,
        llm: Any,
        metadata: ToolMetadata,
        resolve_input_errors: bool = True,
        do_handle_response: bool = True,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(agent)
        self.do_handle_response: bool = do_handle_response
        self.llm = llm
        if not llm:
            raise ValueError("LLM must be provided.")
        self._metadata = metadata
        self._resolve_input_errors = resolve_input_errors
        self.agent = agent
        self._do_interrupt: bool = False
        self._synthesis_engine: Optional[RefreshSimpleChatEngine] = None
        self._logger = kwargs.pop("logger", None)
        if self._logger is None:
            from airunner.utils.application.get_logger import get_logger
            from airunner.settings import AIRUNNER_LOG_LEVEL

            self._logger = get_logger(
                self.__class__.__name__, AIRUNNER_LOG_LEVEL
            )

    @property
    def logger(self):
        """
        Get the logger instance for this tool.
        Returns:
            Logger: The logger instance.
        """
        return self._logger

    @classmethod
    def from_defaults(
        cls,
        llm: Any,
        name: Optional[str] = None,
        description: Optional[str] = None,
        return_direct: bool = True,
        resolve_input_errors: bool = True,
        agent: Any = None,
        do_handle_response: bool = True,
    ) -> "SearchEngineTool":
        name = name or "search_engine_tool"
        description = description or (
            "Performs up to 3 unique internet searches for a given query or list of queries and returns a comprehensive, "
            "natural language answer based on the combined search results. Input may be a string or a list of up to 3 unique strings. "
            "Duplicate queries will be ignored. Use this tool when you need to find current information from the internet."
            "Your queries should be concise and specific to get the best results. Try to find the best query based on the context of the conversation."
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
                memory=None,
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
            self.logger.warning(
                "Search results were not a dict. Cannot format for LLM."
            )
        return formatted_results_str

    def prepare_queries(self, *args: Any, **kwargs: Any) -> List[str]:
        """
        Accept either a single query string or a list of up to 3 queries
        """
        queries = kwargs.get("input", None)
        if args and not queries:
            queries = args[0]
        if isinstance(queries, str):
            queries = [queries]
        if not isinstance(queries, list):
            raise ValueError(
                "Input to SearchEngineTool must be a string or a list of strings."
            )
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        queries = unique_queries[:3]
        return queries

    def call(
        self, *args: Any, tool_call: bool = False, **kwargs: Any
    ) -> ToolOutput:
        self.logger.info(
            "Running SearchEngineTool with args: %s, kwargs: %s", args, kwargs
        )
        queries = self.prepare_queries(*args, **kwargs)
        llm_request = kwargs.get("llm_request", LLMRequest.from_default())

        try:
            self.llm.llm_request = llm_request
        except AttributeError:
            self.logger.warning(
                "LLM does not exist or does not have `llm_request` attribute. "
            )

        try:
            chat_history = kwargs.get("chat_history", self.agent.chat_memory)
        except AttributeError:
            chat_history = None

        consolidated_results = self.combined_search_results(
            queries=queries, category=kwargs.get("category", "all")
        )

        response = (
            self.synthesize_response(
                queries=queries,
                clean_documents=consolidated_results,
                chat_history=chat_history or [],
                do_not_display=kwargs.get("do_not_display", False),
                llm_request=llm_request,
            )
            if consolidated_results
            else "I couldn't find relevant information for your query."
        )
        
        self._do_interrupt = False

        return ToolOutput(
            content=str(response),
            tool_name=self.metadata.name,
            raw_input={"input": queries},
            raw_output=response,
        )

    def synthesize_response(
        self,
        queries: List,
        clean_documents: List,
        chat_history: List,
        do_not_display: bool = False,
        llm_request: Optional[LLMRequest] = None,
    ) -> str:
        """Synthesize a conversational response from search results using the chat engine tool.

        Args:
            queries (List): The original user queries.
            clean_documents (List): Deduplicated search results.
            chat_history (List): The chat history for context.
            do_not_display (bool): If True, do not display the response immediately.
            llm_request (Optional[LLMRequest]): LLM request configuration.

        Returns:
            str: The final conversational response from the chat engine tool.
        """
        formatted_results = self._format_search_results(
            {"Consolidated": clean_documents}
        )
        synthesis_prompt = (
            f"User's original queries: {queries}\n\n"
            f"Relevant information found:\n{formatted_results}\n\n"
            "Please provide a comprehensive answer to the user's original queries based on this information."
        )
        self.logger.info(
            "SearchEngineTool: Synthesizing response from combined search results via chat engine tool"
        )
        # Ensure chat_history is a list, not a ChatMemoryBuffer
        if hasattr(chat_history, "get") and not isinstance(chat_history, list):
            chat_history = chat_history.get()
        # Call the chat engine tool directly with the synthesized prompt
        if not hasattr(self.agent, "chat_engine_tool"):
            self.logger.error(
                "Agent does not have a chat_engine_tool. Returning synthesized prompt as fallback."
            )
            return synthesis_prompt
        chat_response = self.agent.chat_engine_tool.call(
            input=synthesis_prompt,
            chat_history=chat_history,
            do_not_display=do_not_display,
            llm_request=llm_request,
            system_prompt="You are an AI assistant. Based on the following search results and the user's original query, ",
            tool_call=True,  # Mark this as a tool call
        )
        return (
            chat_response.content
            if hasattr(chat_response, "content")
            else str(chat_response)
        )

    def combined_search_results(self, queries: List, category: str) -> List:
        all_results = {}
        seen_items = set()  # (title, link) tuples
        consolidated_results = (
            []
        )  # List of unique results across all services/queries
        for idx, query_str in enumerate(queries):
            if idx > 0:
                time.sleep(0.5)  # Rate limit between requests
            if not self._do_interrupt:
                try:
                    self.logger.info(f"SearchEngineTool: Performing search")
                    search_results = (
                        AggregatedSearchTool.aggregated_search_sync(
                            query_str, category
                        )
                    )
                    if search_results and isinstance(search_results, dict):
                        for service, items in search_results.items():
                            if service not in all_results:
                                all_results[service] = []
                            for item in items:
                                # Deduplicate by (title, link)
                                key = (
                                    item.get("title", ""),
                                    item.get("link", ""),
                                )
                                if key not in seen_items:
                                    seen_items.add(key)
                                    all_results[service].append(item)
                                    consolidated_results.append(item)
                    else:
                        self.logger.warning(
                            f"Search returned no valid results for query: {query_str}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error in SearchEngineTool for query '{query_str}': {e}",
                        exc_info=True,
                    )
        return consolidated_results

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

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)
