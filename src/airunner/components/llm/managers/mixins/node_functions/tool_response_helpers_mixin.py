"""Direct tool response helpers for node functions."""

from typing import Any, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


DIRECT_GENERATION_REQUEST_PREFIX = "__DIRECT_GENERATION_REQUEST__:"


class ToolResponseHelpersMixin:
    """Provide direct-tool and fallback response helpers."""

    @staticmethod
    def _extract_direct_generation_prompt(
        tool_content: str,
    ) -> Optional[str]:
        """Return the direct-generation prompt encoded in tool output."""
        if not tool_content.startswith(DIRECT_GENERATION_REQUEST_PREFIX):
            return None
        prompt = tool_content.removeprefix(
            DIRECT_GENERATION_REQUEST_PREFIX
        ).strip()
        return prompt or None

    def _generate_direct_tool_response(
        self,
        prompt_text: str,
    ) -> Optional[AIMessage]:
        """Run one internal generation pass for direct-output tools."""
        stream_internal = getattr(self, "_stream_internal_response", None)
        if not callable(stream_internal):
            return None

        response = stream_internal(
            [
                SystemMessage(
                    content=(
                        "Return only the requested output. Do not add "
                        "conversational preamble, tool references, or "
                        "meta commentary."
                    )
                ),
                HumanMessage(content=prompt_text),
            ],
            {},
            buffer_visible_output=True,
        )
        if response is None:
            return None

        visible_content = str(getattr(response, "content", "") or "")
        visible_content = visible_content.strip()
        if not visible_content:
            return None

        if getattr(self, "_token_callback", None):
            self._token_callback(visible_content)

        return AIMessage(
            content=visible_content,
            additional_kwargs=(
                getattr(response, "additional_kwargs", {}) or {}
            ),
            tool_calls=[],
        )

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

        generation_prompt = self._extract_direct_generation_prompt(
            direct_content
        )
        if generation_prompt is not None:
            generated_message = self._generate_direct_tool_response(
                generation_prompt
            )
            if generated_message is not None:
                return generated_message
            direct_content = (
                "I couldn't complete that direct generation request."
            )

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
        elif tool_name == "analyze_loaded_document":
            response_content = (
                "I prepared the loaded document for whole-document analysis "
                "but still couldn't produce a grounded answer from it. The "
                "document may not contain enough readable content for that "
                "request."
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