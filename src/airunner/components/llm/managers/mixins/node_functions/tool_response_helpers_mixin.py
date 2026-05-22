"""Direct tool response helpers for node functions."""

from typing import Any, List, Optional

from langchain_core.messages import AIMessage


class ToolResponseHelpersMixin:
    """Provide direct-tool and fallback response helpers."""

    def _get_bound_tool(self, tool_name: str) -> Optional[Any]:
        """Return the currently bound tool object by name."""
        for tool in getattr(self, "_tools", []) or []:
            if getattr(tool, "name", None) == tool_name:
                return tool
        return None

    def _should_return_tool_direct(self, tool_name: str) -> bool:
        """Check whether a bound tool should bypass the post-tool model pass."""
        tool = self._get_bound_tool(tool_name)
        return bool(tool and getattr(tool, "return_direct", False))

    def _create_direct_tool_response_message(
        self,
        tool_messages: List[Any],
        tool_name: str,
    ) -> AIMessage:
        """Create an assistant message directly from tool output."""
        direct_content = ""
        for tool_message in reversed(tool_messages):
            if getattr(tool_message, "name", None) == tool_name and getattr(
                tool_message,
                "content",
                None,
            ):
                direct_content = str(tool_message.content).strip()
                break

        if not direct_content and tool_messages:
            direct_content = str(
                getattr(tool_messages[-1], "content", "")
            ).strip()

        return AIMessage(content=direct_content, tool_calls=[])

    def _generate_fallback_response(self, tool_name: str) -> str:
        """Generate fallback response when tool returned insufficient results."""
        if tool_name == "search_web":
            response_content = (
                "I searched the internet but couldn't find relevant "
                "information on that topic. Could you try rephrasing your "
                "question or asking about something else?"
            )
        elif tool_name == "inspect_loaded_documents":
            response_content = (
                "I inspected the loaded documents but couldn't identify "
                "enough detail to answer that clearly."
            )
        elif tool_name == "rag_search":
            response_content = (
                "I searched through the available documents but couldn't "
                "find information about that. The documents may not contain "
                "details on this topic."
            )
        else:
            response_content = (
                "I tried to find information but wasn't able to get useful "
                "results. Could you rephrase your question or try a "
                "different approach?"
            )

        if self._token_callback:
            self._token_callback(response_content)

        return response_content