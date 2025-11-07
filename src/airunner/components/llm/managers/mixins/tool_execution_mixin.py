"""Tool execution mixin for WorkflowManager.

Handles tool execution with status tracking and signal emission.
"""

import re
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

if TYPE_CHECKING:
    from airunner.components.llm.managers.workflow_manager import WorkflowState


class ToolExecutionMixin:
    """Manages tool execution with status tracking and signal emission."""

    def __init__(self):
        """Initialize tool execution mixin."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._tools = []
        self._conversation_id: Optional[int] = None
        self._executed_tools: list[str] = (
            []
        )  # Track tools called in current invocation

    def _execute_tools_with_status(
        self, state: "WorkflowState"
    ) -> "WorkflowState":
        """Custom tool execution node that emits status signals.

        This wraps the standard ToolNode behavior but adds real-time status
        updates that can be displayed in the UI.

        Args:
            state: Workflow state containing messages

        Returns:
            Updated workflow state with tool results
        """
        from langgraph.prebuilt import ToolNode

        # Get the last AIMessage which contains tool_calls
        messages = state["messages"]
        last_message = messages[-1] if messages else None

        if not last_message or not hasattr(last_message, "tool_calls"):
            # No tool calls to execute, just pass through
            return state

        tool_calls = last_message.tool_calls or []

        # Emit "starting" status for each tool
        self._emit_starting_status(tool_calls)

        # Execute tools using standard ToolNode
        tool_node = ToolNode(self._tools)
        result_state = tool_node.invoke(state)

        # Extract tool results and emit "completed" status
        self._emit_completed_status(result_state, tool_calls)

        return result_state

    def _emit_starting_status(self, tool_calls: list):
        """Emit starting status signals for tool calls.

        Args:
            tool_calls: List of tool call dictionaries
        """
        from airunner.enums import SignalCode
        from airunner.components.application.api.api import API

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "")

            # Track this tool execution
            self._executed_tools.append(tool_name)

            query = self._extract_query_from_args(tool_args)

            self.logger.info(f"🔧 Tool starting: {tool_name} - {query}")

            # Emit "starting" status
            API().emit_signal(
                SignalCode.LLM_TOOL_STATUS_SIGNAL,
                {
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "query": query,
                    "status": "starting",
                    "details": None,
                    "conversation_id": self._conversation_id,
                    "timestamp": str(datetime.now()),
                },
            )

    def _emit_completed_status(
        self, result_state: "WorkflowState", tool_calls: list
    ):
        """Emit completed status signals for tool results.

        Args:
            result_state: Workflow state after tool execution
            tool_calls: List of original tool call dictionaries
        """
        from langchain_core.messages import ToolMessage
        from airunner.enums import SignalCode
        from airunner.components.application.api.api import API

        new_messages = result_state.get("messages", [])
        for msg in new_messages:
            if isinstance(msg, ToolMessage):
                # Find the corresponding tool_call
                matching_tool_call = self._find_matching_tool_call(
                    msg.tool_call_id, tool_calls
                )

                if matching_tool_call:
                    tool_name = matching_tool_call.get("name", "unknown")
                    tool_args = matching_tool_call.get("args", {})
                    query = self._extract_query_from_args(tool_args)

                    # Extract details from result (URLs, sources, etc.)
                    details = self._extract_tool_details(
                        tool_name, msg.content
                    )

                    self.logger.info(
                        f"✅ Tool completed: {tool_name} - {details if details else 'success'}"
                    )

                    # Emit "completed" status
                    API().emit_signal(
                        SignalCode.LLM_TOOL_STATUS_SIGNAL,
                        {
                            "tool_id": msg.tool_call_id,
                            "tool_name": tool_name,
                            "query": query,
                            "status": "completed",
                            "details": details,
                            "conversation_id": self._conversation_id,
                            "timestamp": str(datetime.now()),
                        },
                    )

    def _extract_query_from_args(self, tool_args: dict) -> str:
        """Extract primary query/argument from tool arguments.

        Args:
            tool_args: Tool argument dictionary

        Returns:
            Extracted query string (truncated to 50 chars)
        """
        query = (
            tool_args.get("query")
            or tool_args.get("search_query")
            or tool_args.get("prompt")
            or str(tool_args)[:50]
        )
        return query

    def _find_matching_tool_call(
        self, tool_call_id: str, tool_calls: list
    ) -> Optional[dict]:
        """Find tool call matching the given ID.

        Args:
            tool_call_id: Tool call ID to find
            tool_calls: List of tool call dictionaries

        Returns:
            Matching tool call dict or None
        """
        for tc in tool_calls:
            if tc.get("id") == tool_call_id:
                return tc
        return None

    def _extract_tool_details(
        self, tool_name: str, result_content: str
    ) -> Optional[str]:
        """Extract relevant details from tool result for status display.

        Args:
            tool_name: Name of the tool that was executed
            result_content: The result content from the tool

        Returns:
            Brief details string for display (e.g., "foxnews.com, cnn.com")
        """
        if tool_name == "search_web":
            return self._extract_web_search_details(result_content)
        elif tool_name == "rag_search":
            return self._extract_rag_search_details(result_content)
        return None

    def _extract_web_search_details(
        self, result_content: str
    ) -> Optional[str]:
        """Extract domain names from web search results.

        Args:
            result_content: Web search result content

        Returns:
            Comma-separated domain names or None
        """
        urls = re.findall(r"URL: (https?://[^\s]+)", result_content)
        if urls:
            # Extract domain names only
            domains = [url.split("/")[2] for url in urls[:3]]  # Top 3
            return ", ".join(domains)
        return None

    def _extract_rag_search_details(self, result_content: str) -> str:
        """Extract details from RAG search results.

        Args:
            result_content: RAG search result content

        Returns:
            Status string ("no results" or "found results")
        """
        if "No results" in result_content or "couldn't find" in result_content:
            return "no results"
        else:
            return "found results"
