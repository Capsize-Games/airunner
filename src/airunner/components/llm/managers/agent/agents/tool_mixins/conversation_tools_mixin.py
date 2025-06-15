from llama_index.core.tools import FunctionTool
from airunner.components.llm.managers.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)


class ConversationToolsMixin(ToolSingletonMixin):
    """Mixin for conversation-related tools."""

    @property
    def clear_conversation_tool(self):
        def clear_conversation() -> str:
            self.api.llm.clear_history()
            return "Conversation cleared."

        return self._get_or_create_singleton(
            "_clear_conversation_tool",
            FunctionTool.from_defaults,
            clear_conversation,
            return_direct=True,
        )
