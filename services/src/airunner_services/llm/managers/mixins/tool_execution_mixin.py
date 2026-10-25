"""Tool execution mixin for WorkflowManager.

Handles tool execution with status tracking and workflow event sinks.
"""

import re
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from airunner_services.llm.managers.forced_tool_execution_policy import (
    ForcedToolExecutionPolicy,
)
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text
from airunner_services.llm_workflow_events import (
    resolve_llm_workflow_event_sink,
)

if TYPE_CHECKING:
    from airunner_services.llm.workflow_manager import WorkflowState


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

    def _get_forced_tool_policy(self) -> ForcedToolExecutionPolicy:
        """Return the cached forced-tool execution helper."""
        helper = getattr(self, "_forced_tool_policy", None)
        if helper is None:
            helper = ForcedToolExecutionPolicy(self)
            self._forced_tool_policy = helper
        return helper

    def _execute_tools_with_status(
        self, state: "WorkflowState"
    ) -> "WorkflowState":
        """Custom tool execution node that emits status signals.

        This wraps the standard ToolNode behavior but adds real-time status
        updates that can be displayed in the UI.

        NOTE: bind_tools() narrows what the model *should* emit, but the
        model is untrusted input: every call is re-validated server-side
        (known tool, dict args, signature fit) before execution. Invalid
        calls are answered with a tool error and never executed.

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
        if not tool_calls:
            return state

        policy = self._get_forced_tool_policy()
        state, tool_calls, blocked_state = policy.prepare(state, tool_calls)
        if blocked_state is not None:
            return blocked_state

        valid_calls, invalid_errors = self._validate_tool_calls(tool_calls)

        # Emit "starting" status for valid tools only; invalid calls get
        # an immediate error without execution.
        self._emit_starting_status(valid_calls)

        # Sanitize tool functions to ensure docstrings exist before wrapping
        self._sanitize_tool_functions()

        if valid_calls:
            # Execute valid tools using standard ToolNode
            tool_node = ToolNode(self._tools)
            filtered_state = self._state_with_tool_calls(state, valid_calls)
            result_state = tool_node.invoke(filtered_state)
        else:
            result_state = dict(state)

        if invalid_errors:
            result_state = self._append_tool_errors(
                result_state, invalid_errors
            )

        # Extract tool results and emit "completed" status
        self._emit_completed_status(result_state, valid_calls)

        policy.complete(valid_calls)

        return result_state

    def _known_tool_map(self) -> dict:
        """Map known tool names to their callables."""
        known = {}
        for tool in self._tools or []:
            name = getattr(tool, "name", None) or getattr(
                tool, "__name__", None
            )
            if isinstance(name, str) and name:
                known[name] = tool
        return known

    def _validate_tool_calls(self, tool_calls: list) -> tuple:
        """Split model tool calls into valid and rejected.

        A call is valid only when it names a bound tool, carries a
        dict of arguments, and fits that tool's signature (when the
        signature is inspectable). Rejected calls return ``(tool_id,
        error)`` pairs answered with a tool error, never executed.

        Args:
            tool_calls: Raw tool call dictionaries from the model

        Returns:
            (valid_calls, [(tool_call_id, error_message)])
        """
        valid = []
        rejected = []
        known = self._known_tool_map()
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            name = call.get("name", "unknown")
            call_id = call.get("id", "")
            args = call.get("args", {})
            tool = known.get(name)
            if tool is None:
                rejected.append(
                    (call_id, f"Unknown tool '{name}': not a bound tool")
                )
                continue
            if not isinstance(args, dict):
                rejected.append(
                    (
                        call_id,
                        f"Invalid arguments for tool '{name}': "
                        "args must be an object",
                    )
                )
                continue
            mismatch = self._signature_mismatch(tool, args)
            if mismatch is not None:
                rejected.append((call_id, mismatch))
                continue
            valid.append(call)
        return valid, rejected

    def _signature_mismatch(self, tool, args: dict) -> Optional[str]:
        """Check tool args against its signature, if inspectable."""
        import inspect

        target = getattr(tool, "func", tool)
        try:
            params = inspect.signature(target).parameters
        except (TypeError, ValueError):
            return None
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in params.values()
        )
        tool_name = getattr(tool, "name", None) or getattr(
            target, "__name__", "tool"
        )
        unexpected = [
            key for key in args if key not in params and not accepts_kwargs
        ]
        if unexpected:
            return (
                f"Invalid arguments for tool '{tool_name}': "
                f"unexpected argument(s) {sorted(unexpected)}"
            )
        missing = [
            name
            for name, param in params.items()
            if param.default is inspect.Parameter.empty
            and param.kind
            not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
            and name not in args
            and name not in ("api", "agent", "self")
        ]
        if missing:
            return (
                f"Invalid arguments for tool '{tool_name}': "
                f"missing required argument(s) {sorted(missing)}"
            )
        return None

    def _state_with_tool_calls(self, state: "WorkflowState", calls: list):
        """Return state with the last message limited to valid calls."""
        messages = list(state["messages"])
        last_message = messages[-1]
        try:
            messages[-1] = last_message.model_copy(
                update={"tool_calls": list(calls)}
            )
        except Exception:
            from langchain_core.messages import AIMessage

            messages[-1] = AIMessage(
                content=getattr(last_message, "content", ""),
                tool_calls=list(calls),
            )
        return {**state, "messages": messages}

    def _append_tool_errors(self, state: "WorkflowState", errors: list):
        """Append ToolMessage errors for rejected tool calls."""
        from langchain_core.messages import ToolMessage

        messages = list(state.get("messages", []))
        for call_id, message in errors:
            messages.append(
                ToolMessage(content=message, tool_call_id=call_id)
            )
        return {**state, "messages": messages}

    def _get_next_workflow_tool(self, _current_tool: str) -> str | None:
        """Get the next required tool in the coding workflow sequence.
        
        Previously enforced strict tool ordering, but this caused issues when
        workflows were already active or the model correctly chose to skip steps.
        
        Now returns None to allow the model to choose tools freely based on
        the workflow instructions in the system prompt.
        
        Args:
            current_tool: The tool that just executed
            
        Returns:
            None - workflow tool ordering is no longer enforced
        """
        # No longer enforce tool ordering - let the model follow instructions
        # The workflow state and instructions guide it appropriately
        return None

    def _sanitize_tool_functions(self) -> None:
        """Ensure each tool function has a docstring.

        LangChain's StructuredTool.from_function raises ValueError if a function
        lacks both a description and a docstring. Some legacy mixin tools created
        via @tool (langchain.tools) may omit docstrings. This method adds a minimal
        docstring dynamically to prevent runtime failures.
        """
        sanitized = 0
        for func in self._tools:
            # Skip if already documented
            if getattr(func, "__doc__", None):
                continue
            # Attempt to use .description attribute if present
            desc = (
                getattr(func, "description", None)
                or f"Tool function '{getattr(func, 'name', func.__name__)}' automatically documented."
            )
            func.__doc__ = desc  # type: ignore
            sanitized += 1
        if sanitized:
            self.logger.debug(
                "Added fallback docstrings to %d tool(s) missing documentation",
                sanitized,
            )

    def _emit_starting_status(self, tool_calls: list):
        """Emit starting status signals for tool calls.

        Args:
            tool_calls: List of tool call dictionaries
        """
        event_sink = resolve_llm_workflow_event_sink(self)

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "")

            # Track this tool execution
            self._executed_tools.append(tool_name)

            query = self._extract_query_from_args(tool_args)

            self.logger.info(
                "Tool starting: %s (%s)",
                tool_name,
                summarize_text(query, label="query"),
            )

            event_sink.emit_tool_status(
                {
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "tool_arguments": tool_args,
                    "query": query,
                    "status": "starting",
                    "details": None,
                    "conversation_id": self._conversation_id,
                    "request_id": getattr(self, "_current_request_id", None),
                    "timestamp": str(datetime.now()),
                }
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

        event_sink = resolve_llm_workflow_event_sink(self)

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

                    event_sink.emit_tool_status(
                        {
                            "tool_id": msg.tool_call_id,
                            "tool_name": tool_name,
                            "tool_arguments": tool_args,
                            "query": query,
                            "status": "completed",
                            "details": details,
                            "conversation_id": self._conversation_id,
                            "request_id": getattr(
                                self,
                                "_current_request_id",
                                None,
                            ),
                            "timestamp": str(datetime.now()),
                        }
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
