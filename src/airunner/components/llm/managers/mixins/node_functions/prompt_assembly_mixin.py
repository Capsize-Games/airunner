"""Prompt assembly helpers for node functions."""

import re
from typing import List

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


class PromptAssemblyMixin:
    """Build prompts for node-function model invocations."""

    def _build_prompt(self, trimmed_messages: List[BaseMessage]):
        """Build prompt with system message and tool instructions."""
        chat_model = getattr(self, "_chat_model", None)

        if chat_model and getattr(chat_model, "is_vision_model", False):
            escaped_system_prompt = self._escape_system_prompt()
            escaped_system_prompt = self._add_tool_instructions(
                escaped_system_prompt
            )
            escaped_system_prompt = self._add_post_tool_instructions(
                escaped_system_prompt,
                trimmed_messages,
            )
            vision_system = SystemMessage(content=escaped_system_prompt)
            merged_messages: List[BaseMessage] = []

            for message in trimmed_messages:
                if message is None:
                    self.logger.warning(
                        "[VISION PROMPT] Skipping None message while building prompt"
                    )
                    continue

                if (
                    merged_messages
                    and isinstance(message, HumanMessage)
                    and isinstance(merged_messages[-1], HumanMessage)
                ):
                    current_content = merged_messages[-1].content
                    new_content = message.content

                    if isinstance(current_content, list) and isinstance(
                        new_content, list
                    ):
                        merged_messages[-1].content = (
                            current_content + new_content
                        )
                    elif isinstance(current_content, list):
                        merged_messages[-1].content = (
                            current_content + [new_content]
                        )
                    elif isinstance(new_content, list):
                        merged_messages[-1].content = (
                            [current_content] + new_content
                        )
                    else:
                        merged_messages[-1].content = (
                            f"{current_content}\n{new_content}"
                        )

                    self.logger.debug(
                        "[VISION PROMPT] Merged consecutive HumanMessages to maintain alternation"
                    )
                    continue

                merged_messages.append(message)

            vision_messages = [vision_system, *merged_messages]
            has_human = any(
                isinstance(message, HumanMessage)
                for message in vision_messages
            )
            if not has_human:
                self.logger.warning(
                    "[VISION PROMPT] No HumanMessage present after vision prompt build; messages len=%s",
                    len(vision_messages),
                )
            else:
                self.logger.debug(
                    "[VISION PROMPT] Vision messages count=%s (system + %s user/tool msgs)",
                    len(vision_messages),
                    len(vision_messages) - 1,
                )

            return vision_messages

        escaped_system_prompt = self._escape_system_prompt()
        escaped_system_prompt = self._add_tool_instructions(
            escaped_system_prompt
        )
        escaped_system_prompt = self._add_post_tool_instructions(
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

    def _should_include_tool_instructions(
        self, trimmed_messages: List[BaseMessage]
    ) -> bool:
        """Determine whether to include tool instructions in system prompt."""
        if not self._tools:
            return False

        if not trimmed_messages:
            return False

        last = trimmed_messages[-1]
        if last.__class__.__name__ != "HumanMessage":
            return True

        content = (getattr(last, "content", "") or "").strip().lower()
        if len(content) > 25:
            return True

        greeting_patterns = [
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
        ]
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

        normalized = re.sub(r"[!.?,]", "", content)
        if normalized in greeting_patterns:
            return False

        return True

    def _escape_system_prompt(self) -> str:
        """Escape curly braces in system prompt for LangChain."""
        prompt_source = self._system_prompt
        return prompt_source.replace("{", "{{").replace("}", "}}")

    def _get_memory_context_for_prompt(self) -> str:
        """Get memory context to inject into system prompt."""
        try:
            from airunner.components.knowledge.knowledge_base import (
                get_knowledge_base,
            )

            knowledge_base = get_knowledge_base()
            context = knowledge_base.get_context(max_chars=2000)
            if context:
                self.logger.info(
                    f"[MEMORY] Injecting {len(context)} chars of memory context"
                )
            return context
        except Exception as error:
            self.logger.debug(
                f"[MEMORY] Failed to get memory context: {error}"
            )
            return ""

    def _add_tool_instructions(self, system_prompt: str) -> str:
        """Add tool instructions to system prompt if tools are available."""
        if not self._tools or len(self._tools) == 0:
            return system_prompt

        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )

        if tool_calling_mode == "react":
            compact_tools = self._create_compact_tool_list()
            if compact_tools:
                escaped_tools = compact_tools.replace("{", "{{").replace(
                    "}", "}}"
                )
                system_prompt = f"{system_prompt}\n\n{escaped_tools}"

        self.logger.debug(
            "Tools (%s) bound via bind_tools() - chat adapter will format them (mode: %s)",
            len(self._tools),
            tool_calling_mode,
        )

        force_tool = getattr(self, "_force_tool", None)
        if force_tool:
            sequential_instruction = (
                f"\n\n=== IMPORTANT: SEQUENTIAL TOOL EXECUTION REQUIRED ===\n"
                f"You MUST call the '{force_tool}' tool FIRST and ONLY this tool.\n"
                "Respond ONLY with the required tool call.\n"
                "Do NOT write any conversational text, explanation, JSON example, or commentary before or after the tool call.\n"
                f"DO NOT call multiple tools at once.\n"
                f"Call ONE tool, wait for the result, then call the next tool.\n"
                f"This is a WORKFLOW - each step depends on the previous step's result.\n"
                f"=== END INSTRUCTION ===\n"
            )
            system_prompt += sequential_instruction
            self.logger.info(
                f"[TOOL INSTRUCTIONS] Added sequential execution instruction for force_tool='{force_tool}'"
            )

        return system_prompt