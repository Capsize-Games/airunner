"""Conversation management tools."""

from typing import Callable

from airunner_services.llm.managers.tools.conversation_mutation_tools import (
    build_create_new_conversation_tool,
    build_delete_conversation_tool,
    build_switch_conversation_tool,
    build_update_conversation_title_tool,
)
from airunner_services.llm.managers.tools.conversation_query_tools import (
    build_get_conversation_tool,
    build_list_conversations_tool,
    build_search_conversations_tool,
    build_summarize_conversation_tool,
)
from airunner_services.tools.base_tool import BaseTool


class ConversationTools(BaseTool):
    """Provide the conversation-related tool builders."""

    def list_conversations_tool(self) -> Callable:
        """Return the recent-conversation listing tool."""
        return build_list_conversations_tool(self)

    def get_conversation_tool(self) -> Callable:
        """Return the conversation detail tool."""
        return build_get_conversation_tool(self)

    def summarize_conversation_tool(self) -> Callable:
        """Return the conversation summary tool."""
        return build_summarize_conversation_tool(self)

    def update_conversation_title_tool(self) -> Callable:
        """Return the conversation title update tool."""
        return build_update_conversation_title_tool(self)

    def switch_conversation_tool(self) -> Callable:
        """Return the active-conversation switch tool."""
        return build_switch_conversation_tool(self)

    def create_new_conversation_tool(self) -> Callable:
        """Return the new-conversation creation tool."""
        return build_create_new_conversation_tool(self)

    def search_conversations_tool(self) -> Callable:
        """Return the conversation search tool."""
        return build_search_conversations_tool(self)

    def delete_conversation_tool(self) -> Callable:
        """Return the conversation deletion tool."""
        return build_delete_conversation_tool(self)
