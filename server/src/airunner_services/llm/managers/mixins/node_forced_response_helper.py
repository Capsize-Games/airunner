"""Forced-response helpers for node functions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from airunner_services.llm.managers.workflow_response_prompts import (
    build_workflow_continuation_prompt,
    build_workflow_correction_prompt,
    extract_next_workflow_action,
)


class NodeForcedResponseHelper:
    """Handle forced-response and tool-result synthesis workflows."""

    def __init__(self, owner) -> None:
        """Store the owning workflow manager."""
        self._owner = owner

    def force_response_node(self, state) -> Dict[str, Any]:
        """Generate one forced response when tool execution must stop."""
        ai_message_with_tools = None
        for message in reversed(state["messages"]):
            if self.has_tool_calls(message):
                ai_message_with_tools = message
                break
        if not ai_message_with_tools:
            self._owner.logger.error(
                "Force response node called but no AIMessage with tool_calls found"
            )
            return {"messages": []}
        tool_name = ai_message_with_tools.tool_calls[0].get("name")
        tool_messages = self.get_tool_messages(state["messages"])
        all_tool_content = self.combine_tool_results(tool_messages)
        user_question = self.get_user_question(state["messages"])
        generation_kwargs = state.get("generation_kwargs", {})
        if tool_name in self._owner.WORKFLOW_TOOLS:
            self._owner.logger.info(
                "Force response node: Duplicate workflow tool '%s' - adding continuation instructions and routing back to model",
                tool_name,
            )
            continuation_msg = self.create_workflow_continuation_message(
                all_tool_content,
                tool_name,
                user_question,
            )
            self._owner.logger.info(
                "✓ Force response node: Added continuation message, routing to model"
            )
            return {
                "messages": [continuation_msg],
                "workflow_continuation": True,
            }
        if self.should_return_tool_direct(tool_name):
            self._owner.logger.info(
                "Force response node: returning direct tool result for '%s'",
                tool_name,
            )
            return {
                "messages": [
                    self.create_direct_tool_response_message(
                        tool_messages, tool_name
                    )
                ],
                "workflow_continuation": False,
            }
        self._owner.logger.info(
            "Force response node: Generating answer from %s chars across %s tool result(s)",
            len(all_tool_content),
            len(tool_messages),
        )
        forced_message = self.generate_forced_response_message(
            all_tool_content,
            tool_name,
            user_question,
            generation_kwargs,
        )
        self._owner.logger.info(
            "✓ Force response node: Generated %s char response",
            len(forced_message.content) if forced_message.content else 0,
        )
        return {"messages": [forced_message], "workflow_continuation": False}

    @staticmethod
    def has_tool_calls(message: BaseMessage) -> bool:
        """Return whether one message contains tool calls."""
        return hasattr(message, "tool_calls") and message.tool_calls

    @staticmethod
    def get_user_question(messages: List[BaseMessage]) -> str:
        """Return the most recent human message content."""
        for message in reversed(messages):
            if message.__class__.__name__ == "HumanMessage":
                return message.content
        return ""

    @staticmethod
    def get_tool_messages(messages: List[BaseMessage]) -> List[Any]:
        """Return the tool messages from one message list."""
        return [
            message
            for message in messages
            if message.__class__.__name__ == "ToolMessage"
        ]

    @staticmethod
    def combine_tool_results(tool_messages: List[Any]) -> str:
        """Combine tool-result content into one context string."""
        all_tool_content = ""
        for index, tool_message in enumerate(tool_messages, start=1):
            all_tool_content += f"\n--- Tool Result {index} ---\n"
            all_tool_content += tool_message.content
            all_tool_content += "\n"
        return all_tool_content

    def get_bound_tool(self, tool_name: str) -> Optional[Any]:
        """Return the currently bound tool object by name."""
        for tool in getattr(self._owner, "_tools", []) or []:
            if getattr(tool, "name", None) == tool_name:
                return tool
        return None

    def should_return_tool_direct(self, tool_name: str) -> bool:
        """Return whether one bound tool should bypass the model pass."""
        tool = self.get_bound_tool(tool_name)
        return bool(tool and getattr(tool, "return_direct", False))

    def create_direct_tool_response_message(
        self,
        tool_messages: List[Any],
        tool_name: str,
    ) -> AIMessage:
        """Create one assistant message directly from tool output."""
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

    def generate_forced_response_message(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> AIMessage:
        """Generate one full AIMessage from tool results."""
        return self._owner._get_response_synthesizer().generate_forced_response_message(
            tool_content,
            tool_name,
            user_question,
            generation_kwargs,
        )

    def create_workflow_continuation_message(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
    ) -> HumanMessage:
        """Create one HumanMessage with workflow continuation instructions."""
        self._owner.logger.info(
            "Creating workflow continuation message for duplicate '%s' call",
            tool_name,
        )
        next_action = extract_next_workflow_action(tool_content)
        prompt_text = build_workflow_correction_prompt(
            tool_name=tool_name,
            user_question=user_question,
            next_action=next_action,
        )
        return HumanMessage(content=prompt_text)

    def generate_workflow_continuation_response(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> AIMessage:
        """Generate one response that resumes a stuck workflow."""
        self._owner.logger.info(
            "Generating workflow continuation for duplicate '%s' call",
            tool_name,
        )
        next_action = extract_next_workflow_action(tool_content)
        prompt_text = build_workflow_continuation_prompt(
            tool_name=tool_name,
            user_question=user_question,
            tool_content=tool_content,
            next_action=next_action,
        )
        try:
            response_message = self._owner._get_response_generation_helper().stream_model_response(
                [HumanMessage(content=prompt_text)],
                generation_kwargs,
            )
            if response_message:
                return AIMessage(
                    content=response_message.content or "",
                    additional_kwargs=getattr(
                        response_message,
                        "additional_kwargs",
                        {},
                    ),
                    tool_calls=getattr(response_message, "tool_calls", []),
                )
        except Exception as exc:
            self._owner.logger.error(
                "Failed to generate workflow continuation: %s",
                exc,
            )
        fallback = (
            "The workflow has been started but I'm having trouble continuing. "
            "The next step should be to call transition_phase to move to the planning phase."
        )
        if self._owner._token_callback:
            self._owner._token_callback(fallback)
        return AIMessage(content=fallback, tool_calls=[])

    def generate_forced_response(
        self,
        tool_content: str,
        tool_name: str,
        user_question: str,
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Generate one conversational response from tool results."""
        return self._owner._get_response_synthesizer().generate_forced_response_text(
            tool_content,
            tool_name,
            user_question,
            generation_kwargs,
        )

    def generate_response_message_from_results(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        generation_kwargs: Optional[Dict] = None,
    ) -> Optional[AIMessage]:
        """Generate one AIMessage from tool results."""
        return self._owner._get_response_synthesizer().generate_response_message_from_results(
            all_tool_content,
            tool_name,
            user_question,
            generation_kwargs,
        )

    def generate_response_from_results(
        self,
        all_tool_content: str,
        tool_name: str,
        user_question: str = "",
        generation_kwargs: Optional[Dict] = None,
    ) -> str:
        """Generate one text response from tool results."""
        return self._owner._get_response_synthesizer().generate_response_text_from_results(
            all_tool_content,
            tool_name,
            user_question,
            generation_kwargs,
        )
