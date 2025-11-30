"""Conversation management and autonomous control tools."""

from typing import Callable, Optional
from datetime import datetime, timedelta

from langchain.tools import tool

from airunner.components.llm.data.conversation import Conversation
from airunner.components.tools.base_tool import BaseTool
from airunner.enums import SignalCode


class ConversationTools(BaseTool):
    """Mixin class providing conversation management and autonomous control tools."""

    def list_conversations_tool(self) -> Callable:
        """List recent conversations from the database."""

        @tool
        def list_conversations(
            limit: int = 10, days_back: Optional[int] = None
        ) -> str:
            """List recent conversations from the database.

            This allows you to see past conversations and their context.
            Useful for understanding conversation history and finding specific discussions.

            Args:
                limit: Maximum number of conversations to return (default 10)
                days_back: Optional - only show conversations from last N days

            Returns:
                List of conversations with IDs, titles, and timestamps

            Examples:
                list_conversations(limit=5)  # Get 5 most recent
                list_conversations(days_back=7)  # Get conversations from last week
            """
            try:
                from airunner.components.data.session_manager import (
                    session_scope,
                )

                with session_scope() as session:
                    query = session.query(Conversation).order_by(
                        Conversation.id.desc()
                    )

                    if days_back:
                        cutoff = datetime.now() - timedelta(days=days_back)
                        query = query.filter(Conversation.timestamp >= cutoff)

                    conversations = query.limit(limit).all()

                    if not conversations:
                        return "No conversations found."

                    result_parts = [
                        f"Found {len(conversations)} conversation(s):\n"
                    ]
                    for conv in conversations:
                        conv_id = conv.id
                        title = conv.title or "(no title)"
                        timestamp = conv.timestamp.strftime("%Y-%m-%d %H:%M")
                        msg_count = len(conv.value) if conv.value else 0
                        current = " [CURRENT]" if conv.current else ""

                        result_parts.append(
                            f"ID {conv_id}: {title} - {timestamp} ({msg_count} messages){current}"
                        )

                    return "\n".join(result_parts)

            except Exception as e:
                self.logger.error(f"Error listing conversations: {e}")
                return f"Error listing conversations: {str(e)}"

        return list_conversations

    def get_conversation_tool(self) -> Callable:
        """Get full details of a specific conversation."""

        @tool
        def get_conversation(
            conversation_id: int, include_messages: bool = True
        ) -> str:
            """Get detailed information about a specific conversation.

            Retrieves all metadata and optionally all messages from a conversation.
            Use this to understand the context of past discussions.

            Args:
                conversation_id: ID of the conversation to retrieve
                include_messages: Whether to include full message history (default True)

            Returns:
                Conversation details including messages, participants, and metadata

            Usage:
                get_conversation(42)  # Get full conversation #42
                get_conversation(42, include_messages=False)  # Just metadata
            """
            try:
                from airunner.components.data.session_manager import (
                    session_scope,
                )

                with session_scope() as session:
                    conv = (
                        session.query(Conversation)
                        .filter_by(id=conversation_id)
                        .first()
                    )

                    if not conv:
                        return f"Conversation ID {conversation_id} not found."

                    result_parts = [
                        f"Conversation ID: {conv.id}",
                        f"Title: {conv.title or '(no title)'}",
                        f"Created: {conv.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"Participants: {conv.user_name} ↔ {conv.chatbot_name}",
                        f"Messages: {len(conv.value) if conv.value else 0}",
                        f"Status: {'CURRENT' if conv.current else 'archived'}",
                    ]

                    if conv.summary:
                        result_parts.append(f"\nSummary: {conv.summary}")

                    if include_messages and conv.value:
                        result_parts.append("\n--- Messages ---")
                        for i, msg in enumerate(
                            conv.value[-20:], 1
                        ):  # Last 20 messages
                            role = msg.get("name", msg.get("role", "unknown"))
                            content = msg.get("content", "")
                            timestamp = msg.get("timestamp", "")
                            result_parts.append(
                                f"{i}. [{timestamp}] {role}: {content[:100]}{'...' if len(content) > 100 else ''}"
                            )

                    return "\n".join(result_parts)

            except Exception as e:
                self.logger.error(f"Error getting conversation: {e}")
                return f"Error getting conversation: {str(e)}"

        return get_conversation

    def summarize_conversation_tool(self) -> Callable:
        """Summarize a conversation or the current conversation."""

        @tool
        def summarize_conversation(
            conversation_id: Optional[int] = None,
        ) -> str:
            """Generate or retrieve a summary of a conversation.

            Creates a concise summary of the conversation's key points.
            Useful for quickly understanding what was discussed without reading all messages.

            Args:
                conversation_id: Optional ID of conversation to summarize. If None, uses current.

            Returns:
                Summary of the conversation

            Examples:
                summarize_conversation()  # Summarize current conversation
                summarize_conversation(42)  # Summarize conversation #42
            """
            try:
                from airunner.components.data.session_manager import (
                    session_scope,
                )

                with session_scope() as session:
                    if conversation_id:
                        conv = (
                            session.query(Conversation)
                            .filter_by(id=conversation_id)
                            .first()
                        )
                    else:
                        conv = (
                            session.query(Conversation)
                            .filter_by(current=True)
                            .first()
                        )

                    if not conv:
                        return "No conversation found to summarize."

                    # Use existing summary if available
                    if conv.summary:
                        return f"Summary of Conversation {conv.id}:\n{conv.summary}"

                    # Generate new summary
                    summary = conv.summarize()

                    if summary:
                        # Save the summary
                        from airunner.components.data.session_manager import (
                            session_scope as update_scope,
                        )

                        with update_scope() as update_session:
                            update_session.query(Conversation).filter_by(
                                id=conv.id
                            ).update({"summary": summary})
                        return f"Generated summary for Conversation {conv.id}:\n{summary}"
                    else:
                        return f"Conversation {conv.id} has no messages to summarize."

            except Exception as e:
                self.logger.error(f"Error summarizing conversation: {e}")
                return f"Error summarizing conversation: {str(e)}"

        return summarize_conversation

    def update_conversation_title_tool(self) -> Callable:
        """Update the title of a conversation."""

        @tool
        def update_conversation_title(
            title: str, conversation_id: Optional[int] = None
        ) -> str:
            """Set or update the title of a conversation.

            Gives conversations meaningful titles based on their content.
            This helps organize and find conversations later.

            Args:
                title: New title for the conversation
                conversation_id: Optional ID of conversation. If None, uses current.

            Returns:
                Confirmation message

            Examples:
                update_conversation_title("Discussion about Python decorators")
                update_conversation_title("Health advice session", conversation_id=42)
            """
            try:
                from airunner.components.data.session_manager import (
                    session_scope,
                )

                with session_scope() as session:
                    if conversation_id:
                        conv = (
                            session.query(Conversation)
                            .filter_by(id=conversation_id)
                            .first()
                        )
                    else:
                        conv = (
                            session.query(Conversation)
                            .filter_by(current=True)
                            .first()
                        )

                    if not conv:
                        return "No conversation found to update."

                    old_title = conv.title or "(no title)"
                    session.query(Conversation).filter_by(id=conv.id).update(
                        {"title": title}
                    )

                    self.emit_signal(
                        SignalCode.CONVERSATION_TITLE_UPDATED,
                        {"conversation_id": conv.id, "title": title},
                    )

                    return f"Updated conversation {conv.id} title: '{old_title}' → '{title}'"

            except Exception as e:
                self.logger.error(f"Error updating conversation title: {e}")
                return f"Error updating conversation title: {str(e)}"

        return update_conversation_title

    def switch_conversation_tool(self) -> Callable:
        """Switch to a different conversation."""

        @tool
        def switch_conversation(conversation_id: int) -> str:
            """Switch the active conversation to a different one.

            Allows you to navigate between different conversation contexts.
            The switched conversation becomes the current active conversation.

            Args:
                conversation_id: ID of the conversation to switch to

            Returns:
                Confirmation message with conversation details

            Usage:
                switch_conversation(42)  # Switch to conversation #42
            """
            try:
                from airunner.components.data.session_manager import (
                    session_scope,
                )

                with session_scope() as session:
                    conv = (
                        session.query(Conversation)
                        .filter_by(id=conversation_id)
                        .first()
                    )

                    if not conv:
                        return f"Conversation ID {conversation_id} not found."

                    # Mark all conversations as not current
                    session.query(Conversation).update({"current": False})

                    # Mark target conversation as current
                    session.query(Conversation).filter_by(
                        id=conversation_id
                    ).update({"current": True})

                    # Signal the UI to reload conversation
                    self.emit_signal(
                        SignalCode.LOAD_CONVERSATION_SIGNAL,
                        {"conversation_id": conversation_id},
                    )

                    title = conv.title or "(no title)"
                    msg_count = len(conv.value) if conv.value else 0

                    return f"Switched to conversation {conversation_id}: '{title}' ({msg_count} messages)"

            except Exception as e:
                self.logger.error(f"Error switching conversation: {e}")
                return f"Error switching conversation: {str(e)}"

        return switch_conversation

    def create_new_conversation_tool(self) -> Callable:
        """Create a new conversation."""

        @tool
        def create_new_conversation(title: Optional[str] = None) -> str:
            """Create a new conversation and optionally give it a title.

            Starts a fresh conversation context. Useful when changing topics
            or starting a new discussion thread.

            Args:
                title: Optional title for the new conversation

            Returns:
                Confirmation with new conversation ID

            Usage:
                create_new_conversation("New topic: Machine Learning")
            """
            try:
                conv = Conversation.create()

                if not conv:
                    return "Failed to create new conversation."

                if title:
                    from airunner.components.data.session_manager import (
                        session_scope,
                    )

                    with session_scope() as session:
                        session.query(Conversation).filter_by(
                            id=conv.id
                        ).update({"title": title})

                # Signal UI to switch to new conversation
                self.emit_signal(
                    SignalCode.NEW_CONVERSATION_SIGNAL,
                    {"conversation_id": conv.id},
                )

                title_str = f" with title '{title}'" if title else ""
                return f"Created new conversation {conv.id}{title_str}"

            except Exception as e:
                self.logger.error(f"Error creating conversation: {e}")
                return f"Error creating conversation: {str(e)}"

        return create_new_conversation

    def search_conversations_tool(self) -> Callable:
        """Search conversations by content or metadata."""

        @tool
        def search_conversations(
            query: str, limit: int = 10, search_messages: bool = True
        ) -> str:
            """Search through conversations to find specific topics or content.

            Searches conversation titles, summaries, and optionally message content.
            Helps you find past discussions on specific topics.

            Args:
                query: Search query (keywords to find)
                limit: Maximum results to return (default 10)
                search_messages: Whether to search message content (default True)

            Returns:
                List of matching conversations

            Usage:
                search_conversations("Python decorators")
                search_conversations("health advice", search_messages=False)
            """
            try:
                from airunner.components.data.session_manager import (
                    session_scope,
                )

                with session_scope() as session:
                    conversations = (
                        session.query(Conversation)
                        .order_by(Conversation.id.desc())
                        .all()
                    )

                    query_lower = query.lower()
                    matches = []

                    for conv in conversations:
                        score = 0

                        # Search title
                        if conv.title and query_lower in conv.title.lower():
                            score += 10

                        # Search summary
                        if (
                            conv.summary
                            and query_lower in conv.summary.lower()
                        ):
                            score += 5

                        # Search messages
                        if search_messages and conv.value:
                            for msg in conv.value:
                                content = msg.get("content", "").lower()
                                if query_lower in content:
                                    score += 1

                        if score > 0:
                            matches.append((score, conv))

                    # Sort by score and take top results
                    matches.sort(reverse=True, key=lambda x: x[0])
                    top_matches = matches[:limit]

                    if not top_matches:
                        return f"No conversations found matching '{query}'"

                    result_parts = [
                        f"Found {len(top_matches)} conversation(s) matching '{query}':\n"
                    ]

                    for score, conv in top_matches:
                        title = conv.title or "(no title)"
                        timestamp = conv.timestamp.strftime("%Y-%m-%d")
                        msg_count = len(conv.value) if conv.value else 0
                        result_parts.append(
                            f"ID {conv.id} [score: {score}]: {title} - {timestamp} ({msg_count} msgs)"
                        )

                    return "\n".join(result_parts)

            except Exception as e:
                self.logger.error(f"Error searching conversations: {e}")
                return f"Error searching conversations: {str(e)}"

        return search_conversations

    def delete_conversation_tool(self) -> Callable:
        """Delete a conversation from the database."""

        @tool
        def delete_conversation(
            conversation_id: int, confirm: bool = False
        ) -> str:
            """Delete a conversation permanently.

            USE WITH CAUTION! This permanently removes a conversation.
            Requires confirmation flag to prevent accidents.

            Args:
                conversation_id: ID of conversation to delete
                confirm: Must be True to actually delete (safety check)

            Returns:
                Confirmation or warning message

            Usage:
                delete_conversation(42, confirm=True)
            """
            try:
                if not confirm:
                    return (
                        f"WARNING: This will permanently delete conversation {conversation_id}. "
                        "Call again with confirm=True to proceed."
                    )

                from airunner.components.data.session_manager import (
                    session_scope,
                )

                with session_scope() as session:
                    conv = (
                        session.query(Conversation)
                        .filter_by(id=conversation_id)
                        .first()
                    )

                    if not conv:
                        return f"Conversation ID {conversation_id} not found."

                    title = conv.title or "(no title)"

                    # Don't allow deleting current conversation
                    if conv.current:
                        return "Cannot delete the current active conversation. Switch to another first."

                    Conversation.delete(pk=conversation_id)

                    self.emit_signal(
                        SignalCode.CONVERSATION_DELETED,
                        {"conversation_id": conversation_id},
                    )

                    return f"Deleted conversation {conversation_id}: '{title}'"

            except Exception as e:
                self.logger.error(f"Error deleting conversation: {e}")
                return f"Error deleting conversation: {str(e)}"

        return delete_conversation
