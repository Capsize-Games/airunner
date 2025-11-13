"""
Tool Execution Mixin - Handles tool invocation and execution.

This mixin provides tool execution functionality for the Deep Research Agent:
- Tool retrieval and binding
- Model invocation with tools
- Tool call execution and error handling
- Phase execution with tool loops
"""

import inspect
from typing import Any, Dict, List
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ToolExecutionMixin:
    """Mixin for tool execution in Deep Research Agent."""

    def _get_research_tools(self) -> List[Any]:
        """Get RESEARCH and SEARCH category tools from registry.

        Returns:
            List of LangChain StructuredTool objects
        """
        research_tools = ToolRegistry.get_by_category(ToolCategory.RESEARCH)
        search_tools = ToolRegistry.get_by_category(ToolCategory.SEARCH)

        all_tools = research_tools + search_tools
        logger.info(
            f"Deep Research: {len(research_tools)} RESEARCH + "
            f"{len(search_tools)} SEARCH = {len(all_tools)} tools"
        )

        logger.debug(f"RESEARCH tools: {[t.name for t in research_tools]}")
        logger.debug(f"SEARCH tools: {[t.name for t in search_tools]}")

        langchain_tools = [
            StructuredTool.from_function(
                func=tool_info.func,
                name=tool_info.name,
                description=tool_info.description,
                return_direct=tool_info.return_direct,
            )
            for tool_info in all_tools
        ]

        logger.info(
            f"Converted {len(langchain_tools)} tools to LangChain format"
        )
        logger.debug(
            f"Available tool names: {[t.name for t in langchain_tools]}"
        )
        return langchain_tools

    def _log_model_invocation(
        self, phase_name: str, task_prompt: str, messages: list, iteration: int
    ) -> None:
        """Log detailed information about model invocation."""
        logger.debug(
            f"[{phase_name}] Iteration {iteration} - Sending to model:"
        )
        logger.debug(f"  System prompt: {self._system_prompt[:100]}...")
        logger.debug(f"  Task prompt: {task_prompt[:100]}...")
        logger.debug(f"  Messages count: {len(messages)}")

        if messages:
            first_msg_content = (
                messages[0].content[:100]
                if hasattr(messages[0], "content")
                else str(messages[0])[:100]
            )
            logger.debug(f"  First message: {first_msg_content}...")

    def _log_model_response(self, phase_name: str, response: Any) -> None:
        """Log detailed information about model response."""
        logger.debug(f"[{phase_name}] Model response type: {type(response)}")

        if hasattr(response, "content"):
            content_preview = (
                response.content[:200] if response.content else "(empty)"
            )
            logger.debug(
                f"[{phase_name}] Model response content: {content_preview}..."
            )

        if hasattr(response, "tool_calls"):
            logger.debug(
                f"[{phase_name}] Model tool_calls: {response.tool_calls}"
            )

    def _invoke_model_with_tools(
        self, phase_name: str, task_prompt: str, messages: list, iteration: int
    ) -> Any:
        """Invoke the chat model with tools for a phase iteration."""
        self._log_model_invocation(
            phase_name, task_prompt, messages, iteration
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._system_prompt),
                ("system", task_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        chain = prompt | self._chat_model
        response = chain.invoke({"messages": messages})

        self._log_model_response(phase_name, response)
        return response

    def _find_tool_by_name(self, tool_name: str) -> Any:
        """Find a tool object by name."""
        for tool in self._tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                return tool
        return None

    def _execute_tool_invocation(
        self, tool_obj: Any, tool_name: str, tool_args: Dict, phase_name: str
    ) -> str:
        """Execute the actual tool invocation with proper argument handling."""
        func = tool_obj.func if hasattr(tool_obj, "func") else tool_obj.run
        sig = inspect.signature(func)

        if "api" in sig.parameters and self._api:
            tool_args["api"] = self._api

        result = tool_obj.invoke(tool_args)
        logger.debug(f"[{phase_name}] Tool {tool_name} executed successfully")
        return str(result)

    def _check_cached_tool_result(
        self, tool_name: str, state: dict, phase_name: str, tool_id: str
    ) -> ToolMessage:
        """Check if tool result can be reused from cache.

        Returns:
            ToolMessage if cached, None otherwise
        """
        if tool_name == "create_research_document" and state.get(
            "document_path"
        ):
            logger.info(f"[{phase_name}] Reusing existing document path")
            return ToolMessage(
                content=str(state["document_path"]), tool_call_id=tool_id
            )

        if tool_name == "create_research_notes" and state.get("notes_path"):
            logger.info(f"[{phase_name}] Reusing existing notes path")
            return ToolMessage(
                content=str(state["notes_path"]), tool_call_id=tool_id
            )

        return None

    def _execute_single_tool(
        self,
        tool_call: dict,
        phase_name: str,
        state: dict,
        state_updates: dict,
    ) -> ToolMessage:
        """Execute a single tool call and return the result message."""
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        tool_args = self._normalize_tool_args(tool_name, tool_args, state)
        tool_id = tool_call.get("id")

        # Check for cached results
        cached_result = self._check_cached_tool_result(
            tool_name, state, phase_name, tool_id
        )
        if cached_result:
            return cached_result

        # Find and execute tool
        tool_obj = self._find_tool_by_name(tool_name)
        if not tool_obj:
            logger.warning(f"[{phase_name}] Tool {tool_name} not found")
            return ToolMessage(
                content=f"Error: Tool {tool_name} not found",
                tool_call_id=tool_id,
            )

        try:
            result = self._execute_tool_invocation(
                tool_obj, tool_name, tool_args, phase_name
            )
            self._apply_tool_side_effects(
                tool_name, result, state_updates, state
            )
            return ToolMessage(content=result, tool_call_id=tool_id)
        except Exception as e:
            logger.error(
                f"[{phase_name}] Tool {tool_name} failed: {e}", exc_info=True
            )
            return ToolMessage(
                content=f"Error: {str(e)}", tool_call_id=tool_id
            )
