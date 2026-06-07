"""Prompt-assembly helpers for node functions."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    trim_messages,
)
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


class NodePromptAssemblyHelper:
    """Build prompts and model-call inputs for workflow nodes."""

    def __init__(self, owner) -> None:
        """Store the owning workflow manager."""
        self._owner = owner

    def call_model(self, state) -> Dict[str, Any]:
        """Call the model with trimmed message history."""
        messages = state["messages"]
        self._owner.logger.info(
            "[CALL MODEL DEBUG] Total messages in state: %s",
            len(messages),
        )
        for index, message in enumerate(messages[-5:]):
            msg_type = type(message).__name__
            content_preview = (
                str(message.content)[:100]
                if hasattr(message, "content")
                else "No content"
            )
            self._owner.logger.info(
                "[CALL MODEL DEBUG] Message %s: %s - %s",
                index,
                msg_type,
                content_preview,
            )
        generation_kwargs = state.get("generation_kwargs", {})
        chat_model = getattr(self._owner, "_chat_model", None)
        if chat_model and getattr(chat_model, "is_vision_model", False):
            trimmed_messages = state["messages"]
        else:
            trimmed_messages = self.trim_messages(state["messages"])
        prompt = self.build_prompt(trimmed_messages)
        self._owner._assistant_turn_index = (
            getattr(
                self._owner,
                "_assistant_turn_index",
                0,
            )
            + 1
        )
        response_message = (
            self._owner._get_response_generation_helper().generate_response(
                prompt,
                generation_kwargs,
            )
        )
        if response_message is None:
            self._owner.logger.error(
                "[CALL MODEL DEBUG] Model returned no message; emitting fallback AIMessage"
            )
            response_message = AIMessage(
                content="",
                additional_kwargs={"error": "no_message_generated"},
                tool_calls=[],
            )
        # If a previous message had tool calls, prepend its <tool_call>
        # XML so the client-side parser can render the tool call widget.
        # Only do this when the response is NOT itself a tool call (which
        # would already have its own XML).
        resp_content = str(getattr(response_message, "content", "") or "")
        if resp_content and "<tool_call>" not in resp_content:
            for prev in reversed(state["messages"]):
                if hasattr(prev, "tool_calls") and prev.tool_calls:
                    src = str(getattr(prev, "content", "") or "")
                    if "<tool_call>" in src:
                        response_message = AIMessage(
                            content=src + "\n" + resp_content,
                            additional_kwargs=getattr(
                                response_message,
                                "additional_kwargs",
                                {},
                            )
                            or {},
                            tool_calls=[],
                        )
                    break
        return {"messages": [response_message]}

    def trim_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim message history to fit the configured context window."""
        return trim_messages(
            messages,
            max_tokens=self._owner._max_history_tokens,
            strategy="last",
            token_counter=self._owner._token_counter,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

    def build_prompt(self, trimmed_messages: List[BaseMessage]):
        """Build one prompt with system, tools, and post-tool guidance."""
        chat_model = getattr(self._owner, "_chat_model", None)
        if chat_model and getattr(chat_model, "is_vision_model", False):
            return self._build_vision_prompt(trimmed_messages)
        escaped_system_prompt = self.escape_system_prompt()
        escaped_system_prompt = self.add_tool_instructions(
            escaped_system_prompt
        )
        escaped_system_prompt = self._owner._get_post_tool_instructions_helper().add_post_tool_instructions(
            escaped_system_prompt,
            trimmed_messages,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", escaped_system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        return prompt.invoke({"messages": trimmed_messages})

    def _build_vision_prompt(self, trimmed_messages: List[BaseMessage]):
        """Build one vision prompt while preserving multimodal messages."""
        escaped_system_prompt = self.escape_system_prompt()
        escaped_system_prompt = self.add_tool_instructions(
            escaped_system_prompt
        )
        escaped_system_prompt = self._owner._get_post_tool_instructions_helper().add_post_tool_instructions(
            escaped_system_prompt,
            trimmed_messages,
        )
        vision_system = SystemMessage(content=escaped_system_prompt)
        merged_messages: List[BaseMessage] = []
        for message in trimmed_messages:
            if message is None:
                self._owner.logger.warning(
                    "[VISION PROMPT] Skipping None message while building prompt"
                )
                continue
            if (
                merged_messages
                and isinstance(message, HumanMessage)
                and isinstance(merged_messages[-1], HumanMessage)
            ):
                self._merge_human_content(merged_messages[-1], message)
                self._owner.logger.debug(
                    "[VISION PROMPT] Merged consecutive HumanMessages to maintain alternation"
                )
                continue
            merged_messages.append(message)
        vision_messages = [vision_system, *merged_messages]
        has_human = any(
            isinstance(message, HumanMessage) for message in vision_messages
        )
        if not has_human:
            self._owner.logger.warning(
                "[VISION PROMPT] No HumanMessage present after vision prompt build; messages len=%s",
                len(vision_messages),
            )
        else:
            self._owner.logger.debug(
                "[VISION PROMPT] Vision messages count=%s (system + %s user/tool msgs)",
                len(vision_messages),
                len(vision_messages) - 1,
            )
        return vision_messages

    @staticmethod
    def _merge_human_content(
        target: HumanMessage, message: HumanMessage
    ) -> None:
        """Merge one human message into the previous human message."""
        current_content = target.content
        new_content = message.content
        if isinstance(current_content, list) and isinstance(new_content, list):
            target.content = current_content + new_content
            return
        if isinstance(current_content, list):
            target.content = current_content + [new_content]
            return
        if isinstance(new_content, list):
            target.content = [current_content] + new_content
            return
        target.content = f"{current_content}\n{new_content}"

    def should_include_tool_instructions(
        self,
        trimmed_messages: List[BaseMessage],
    ) -> bool:
        """Return whether tool instructions should be injected."""
        if not self._owner._tools or not trimmed_messages:
            return False
        last = trimmed_messages[-1]
        if last.__class__.__name__ != "HumanMessage":
            return True
        content = (getattr(last, "content", "") or "").strip().lower()
        if len(content) > 25:
            return True
        action_keywords = [
            "solve",
            "calculate",
            "search",
            "find",
            "create",
            "generate",
            "update",
            "schedule",
            "plot",
            "graph",
        ]
        if any(keyword in content for keyword in action_keywords):
            return True
        greeting_patterns = {
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "yo",
        }
        normalized = re.sub(r"[!.?,]", "", content)
        return normalized not in greeting_patterns

    def escape_system_prompt(self) -> str:
        """Escape curly braces in the stored system prompt."""
        prompt_source = self._owner._system_prompt
        return prompt_source.replace("{", "{{").replace("}", "}}")

    def get_memory_context_for_prompt(self) -> str:
        """Return one best-effort memory context string for prompts."""
        try:
            from airunner_services.knowledge import get_knowledge_base

            knowledge_base = get_knowledge_base()
            context = knowledge_base.get_context(max_chars=2000)
            if context:
                self._owner.logger.info(
                    "[MEMORY] Injecting %s chars of memory context",
                    len(context),
                )
            return context
        except Exception as exc:
            self._owner.logger.debug(
                "[MEMORY] Failed to get memory context: %s",
                exc,
            )
            return ""

    def add_tool_instructions(self, system_prompt: str) -> str:
        """Add compact tool instructions when the active mode needs them."""
        if not self._owner._tools:
            return system_prompt
        tool_calling_mode = getattr(
            self._owner._chat_model, "tool_calling_mode", "react"
        )
        if tool_calling_mode == "react":
            compact_tools = self._owner._create_compact_tool_list()
            if compact_tools:
                escaped_tools = compact_tools.replace("{", "{{").replace(
                    "}", "}}"
                )
                system_prompt = f"{system_prompt}\n\n{escaped_tools}"
        self._owner.logger.debug(
            "Tools (%s) bound via bind_tools() - chat adapter will format them (mode: %s)",
            len(self._owner._tools),
            tool_calling_mode,
        )
        force_tool = getattr(self._owner, "_force_tool", None)
        if not force_tool:
            return system_prompt
        system_prompt += (
            "\n\n=== IMPORTANT: SEQUENTIAL TOOL EXECUTION REQUIRED ===\n"
            f"You MUST call the '{force_tool}' tool FIRST and ONLY this tool.\n"
            "DO NOT call multiple tools at once.\n"
            "Call ONE tool, wait for the result, then call the next tool.\n"
            "This is a WORKFLOW - each step depends on the previous step's result.\n"
            "=== END INSTRUCTION ===\n"
        )
        self._owner.logger.info(
            "[TOOL INSTRUCTIONS] Added sequential execution instruction for force_tool='%s'",
            force_tool,
        )
        return system_prompt
