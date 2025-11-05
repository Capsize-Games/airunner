"""
Conversation and chat tools.

Tools for managing conversations, chat history, and user interactions.
"""

from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory


@tool(
    name="clear_chat_history",
    category=ToolCategory.CONVERSATION,
    description="Clear the current chat conversation history",
    return_direct=True,
    requires_agent=True,
)
def clear_chat_history(agent: Any = None) -> str:
    """Clear chat history."""
    if agent and hasattr(agent, "clear_history"):
        agent.clear_history()
        return "Chat history cleared"
    return "Unable to clear history"


@tool(
    name="get_conversation_summary",
    category=ToolCategory.CONVERSATION,
    description="Get a summary of the current conversation",
    return_direct=False,
    requires_agent=True,
)
def get_conversation_summary(agent: Any = None) -> str:
    """Get conversation summary."""
    if agent and hasattr(agent, "get_conversation_summary"):
        return agent.get_conversation_summary()
    return "No summary available"


@tool(
    name="load_conversation",
    category=ToolCategory.CONVERSATION,
    description="Load a saved conversation by ID",
    return_direct=True,
    requires_agent=True,
)
def load_conversation(
    conversation_id: Annotated[int, "ID of conversation to load"],
    agent: Any = None,
) -> str:
    """Load a conversation."""
    if agent and hasattr(agent, "load_conversation"):
        agent.load_conversation({"conversation_id": conversation_id})
        return f"Loaded conversation {conversation_id}"
    return "Unable to load conversation"
