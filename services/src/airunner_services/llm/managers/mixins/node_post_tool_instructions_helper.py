"""Post-tool instruction helpers for node functions."""

from __future__ import annotations

from typing import List

from langchain_core.messages import BaseMessage

from airunner_services.llm.managers.mixins.node_research_post_tool_helper import (
    NodeResearchPostToolHelper,
)


class NodePostToolInstructionsHelper:
    """Build post-tool guidance for the workflow model."""

    TASK_COMPLETING_TOOLS = {"write_file", "complete_todo_item"}

    def __init__(self, owner) -> None:
        """Store the owning workflow manager."""
        self._owner = owner
        self._research_helper = NodeResearchPostToolHelper()

    def add_post_tool_instructions(
        self,
        system_prompt: str,
        trimmed_messages: List[BaseMessage],
    ) -> str:
        """Add post-tool execution instructions when tool results exist."""
        tool_messages = self._tool_messages(trimmed_messages)
        if not tool_messages:
            return system_prompt
        error_instruction = self._error_instruction(tool_messages)
        if error_instruction:
            self._owner.logger.info(
                "[POST-TOOL] Tool returned ERROR - injecting error handling instructions"
            )
            return f"{system_prompt}{error_instruction}"
        instruction = self._build_instruction(trimmed_messages, tool_messages)
        system_prompt += instruction
        self._owner.logger.info("[POST-TOOL] Full instruction text:\n%s", instruction)
        self._log_tool_results(tool_messages)
        return system_prompt

    @staticmethod
    def _tool_messages(trimmed_messages: List[BaseMessage]) -> List[BaseMessage]:
        """Return the tool messages from one trimmed message list."""
        return [
            message
            for message in trimmed_messages
            if message.__class__.__name__ == "ToolMessage"
        ]

    def _error_instruction(self, tool_messages: List[BaseMessage]) -> str:
        """Return one error-recovery instruction when a tool failed."""
        error_results = []
        for tool_message in tool_messages:
            content = str(getattr(tool_message, "content", ""))
            if content.startswith("ERROR:") or content.startswith("Error:"):
                error_results.append(content)
        if not error_results:
            return ""
        return (
            "\n\n=== CRITICAL: TOOL RETURNED AN ERROR - YOU MUST CALL A TOOL ===\n"
            "The previous tool call FAILED. Read the error message carefully.\n\n"
            "**ERROR MESSAGE:**\n"
            f"{error_results[-1][:800]}\n\n"
            "**YOU MUST DO ONE OF THESE:**\n"
            "1. Call the tool suggested in the error message (e.g., transition_phase, add_todo_item, start_todo_item)\n"
            "2. Follow the workflow steps exactly as described in the error\n\n"
            "**DO NOT:**\n"
            "- Claim the file was created (IT WAS NOT)\n"
            "- Skip workflow steps\n"
            "- Respond with text saying you completed the task\n"
            "- Give the user any output without first fixing the workflow state\n\n"
            "**NEXT ACTION:** Call one of these workflow tools:\n"
            "- transition_phase('planning', 'reason') - to move to next phase\n"
            "- add_todo_item('title', 'description') - to create a task\n"
            "- start_todo_item('todo_1') - to begin working on a task\n\n"
            "Call a tool NOW. Do not respond with text."
        )

    def _build_instruction(
        self,
        trimmed_messages: List[BaseMessage],
        tool_messages: List[BaseMessage],
    ) -> str:
        """Return the post-tool instruction for the current workflow mode."""
        response_format = getattr(self._owner, "_response_format", None)
        force_tool = getattr(self._owner, "_force_tool", None)
        tool_calling_mode = getattr(self._owner._chat_model, "tool_calling_mode", "react")
        tool_call_count = len(
            [message for message in trimmed_messages if hasattr(message, "tool_calls") and message.tool_calls]
        )
        scrape_attempts = sum(
            1
            for message in trimmed_messages
            if hasattr(message, "tool_calls") and message.tool_calls
            for tool_call in message.tool_calls
            if tool_call.get("name") == "scrape_website"
        )
        successful_scrapes, failed_scrapes = self._research_helper.scrape_counts(
            tool_messages
        )
        search_urls = self._research_helper.search_urls(tool_messages)
        self._owner.logger.info(
            "[POST-TOOL] response_format=%s, tool_calling_mode=%s, force_tool=%s, "
            "is_research_mode=%s, tool_calls=%s, scrape_attempts=%s, "
            "successful_scrapes=%s, failed_scrapes=%s, search_urls=%s",
            response_format,
            tool_calling_mode,
            force_tool,
            force_tool == "search_web",
            tool_call_count,
            scrape_attempts,
            successful_scrapes,
            failed_scrapes,
            len(search_urls),
        )
        if force_tool == "search_web":
            return self._research_helper.research_instruction(
                tool_call_count,
                scrape_attempts,
                successful_scrapes,
                failed_scrapes,
                search_urls,
            )
        if response_format == "json":
            return (
                "\n\n=== CRITICAL RESPONSE FORMAT REQUIREMENT ===\n"
                "You have tool results in the conversation above. "
                "Now answer the user's question using that information.\n"
                "YOU MUST respond ONLY with valid JSON in the EXACT format specified in the system prompt above.\n"
                "Do NOT write conversational text. Do NOT explain or narrate. ONLY output the JSON object.\n"
                "Your entire response must be parseable JSON - nothing else."
            )
        if response_format is not None and response_format != "conversational":
            return (
                "\n\n=== CRITICAL: USE TOOL RESULTS ===\n"
                "You have tool results in the conversation above. "
                "Answer the user's question using that information. "
                f"Respond in {response_format} format."
            )
        return self._default_instruction(trimmed_messages, tool_messages)

    def _default_instruction(
        self,
        trimmed_messages: List[BaseMessage],
        tool_messages: List[BaseMessage],
    ) -> str:
        """Return the default post-tool instruction for conversational mode."""
        last_tool_name = self._last_tool_name(trimmed_messages)
        tool_succeeded = self._tool_succeeded(tool_messages)
        if last_tool_name in self.TASK_COMPLETING_TOOLS and tool_succeeded:
            self._owner.logger.info(
                "[POST-TOOL] Task-completing tool '%s' succeeded - instructing model to respond (not call more tools)",
                last_tool_name,
            )
            return (
                "\n\n=== TASK COMPLETED - RESPOND TO USER ===\n"
                "The requested task has been completed successfully!\n\n"
                "**YOUR NEXT ACTION:** Respond to the user with a summary.\n"
                "- Tell them what was accomplished\n"
                "- Include the file path or result from the tool output\n"
                "- Keep it brief and friendly\n\n"
                "**DO NOT:**\n"
                "- Call more tools (the task is DONE)\n"
                "- Start a new task without being asked\n"
                "- Give a generic greeting\n\n"
                "Example response: 'Done! I created hello_world.py with your function.'"
            )
        return (
            "\n\n=== CRITICAL: USE TOOL RESULTS ===\n"
            "Tool results are available in the conversation above.\n"
            "IMPORTANT: You MUST use these tool results to answer the user's question.\n"
            "Do NOT ignore the tool results. Do NOT give a generic greeting.\n"
            "Synthesize the information from the tool results into a helpful, conversational response.\n"
            "If the tool returned search results, summarize the key information for the user."
        )

    @staticmethod
    def _last_tool_name(trimmed_messages: List[BaseMessage]) -> str | None:
        """Return the last requested tool name from AI messages."""
        ai_messages = [
            message
            for message in trimmed_messages
            if hasattr(message, "tool_calls") and message.tool_calls
        ]
        if not ai_messages or not ai_messages[-1].tool_calls:
            return None
        return ai_messages[-1].tool_calls[-1].get("name")

    @staticmethod
    def _tool_succeeded(tool_messages: List[BaseMessage]) -> bool:
        """Return whether the last tool message indicates success."""
        if not tool_messages:
            return False
        last_tool_content = str(getattr(tool_messages[-1], "content", ""))
        indicators = ["created", "successfully", "written", "✓", "complete", "done"]
        return any(indicator in last_tool_content.lower() for indicator in indicators)

    def _log_tool_results(self, tool_messages: List[BaseMessage]) -> None:
        """Log previews of available tool results."""
        self._owner.logger.info(
            "Model has access to %s tool result(s)",
            len(tool_messages),
        )
        for index, tool_message in enumerate(tool_messages, start=1):
            result_preview = (
                tool_message.content[:200]
                if hasattr(tool_message, "content")
                else "No content"
            )
            self._owner.logger.info(
                "  Tool result %s preview: %s...",
                index,
                result_preview,
            )