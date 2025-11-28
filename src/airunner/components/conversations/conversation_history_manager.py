"""Manages loading and formatting of conversation history."""

from typing import Any, Dict, List, Optional

from airunner.components.llm.data.conversation import Conversation
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ConversationHistoryManager:
    """Handles fetching and formatting of conversation history.

    This manager provides a centralized way to access conversation data,
    decoupling UI components and other services from the specifics of
    how conversations are stored or whether an LLM agent is active.
    """

    def __init__(self) -> None:
        """Initializes the ConversationHistoryManager."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def _extract_query_from_tool_call(self, tool_call: Dict[str, Any]) -> str:
        """Extract a user-friendly query string from a tool call.

        Args:
            tool_call: Tool call dictionary with 'args' field

        Returns:
            Query string for display
        """
        args = tool_call.get("args", {})
        if isinstance(args, dict):
            # Try common query field names
            for key in ("query", "search_query", "prompt", "input", "question"):
                if key in args:
                    return str(args[key])
            # Fallback: return first string value
            for value in args.values():
                if isinstance(value, str) and value:
                    return value
        return ""

    def get_current_conversation(self) -> Optional[Conversation]:
        """Fetches the current conversation.

        Returns:
            Optional[Conversation]: The current conversation object, or None
                                     if no current conversation exists.
        """
        conversations = Conversation.objects.filter_by(current=True)
        if len(conversations) == 0:
            self.logger.info("No current conversation found.")
            return None
        self.logger.debug("Fetching the current conversation.")
        try:
            conversation = conversations[0]
            if conversation:
                self.logger.info(f"Current conversation ID: {conversation.id}")
                return conversation
            self.logger.info("No current conversation found.")
            return None
        except Exception as e:
            self.logger.error(
                f"Error fetching current conversation: {e}",
                exc_info=True,
            )
            return None

    def get_most_recent_conversation_id(self) -> Optional[int]:
        """Fetches the ID of the most recent conversation.

        Returns:
            Optional[int]: The ID of the most recent conversation, or None
                           if no conversations exist.
        """
        self.logger.debug("Fetching the most recent conversation ID.")
        try:
            conversation = Conversation.most_recent()
            if conversation:
                self.logger.info(
                    f"Most recent conversation ID: {conversation.id}"
                )
                return conversation.id
            self.logger.info("No conversations found.")
            return None
        except Exception as e:
            self.logger.error(
                f"Error fetching most recent conversation ID: {e}",
                exc_info=True,
            )
            return None

    def load_conversation_history(
        self,
        conversation: Optional[Conversation] = None,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
    ) -> List[Dict[str, Any]]:
        if conversation is None and conversation_id is not None:
            conversation = Conversation.objects.filter_by_first(
                id=conversation_id
            )
            if conversation is None:
                self.logger.warning(
                    f"Conversation {conversation_id} not found. Returning empty history."
                )
                return []
        elif conversation is None:
            conversation = self.get_current_conversation()

        if conversation is None:
            conversation = Conversation.most_recent()
            if conversation is None:
                self.logger.warning(
                    "No conversation found. Returning empty history."
                )
                return []

        self.logger.debug(
            f"Loading conversation history for ID: {getattr(conversation, 'id', None)} (max: {max_messages})"
        )
        conversation_id = getattr(conversation, "id", None)
        try:
            raw_messages = getattr(conversation, "value", None)
            if not isinstance(raw_messages, list):
                self.logger.warning(
                    f"Conversation {conversation_id} has invalid message data (not a list): {type(raw_messages)}"
                )
                return []
            if not raw_messages:
                self.logger.info(f"Conversation {conversation_id} is empty.")
                return []

            # Apply max_messages limit
            if len(raw_messages) > max_messages:
                raw_messages = raw_messages[-max_messages:]

            # Track URLs from tool results for citation
            pending_citations: List[str] = []
            
            # Track tool calls to attach to subsequent assistant message
            pending_tool_usage: List[Dict[str, Any]] = []
            # Track tool results to get details (domains, etc.)
            pending_tool_results: Dict[str, str] = {}  # tool_call_id -> details
            # Track pre-tool thinking content to attach to assistant message
            pending_pre_tool_thinking: Optional[str] = None

            formatted_messages: List[Dict[str, Any]] = []
            for msg_idx, msg_obj in enumerate(raw_messages):
                if not isinstance(msg_obj, dict):
                    self.logger.warning(
                        f"Skipping invalid message object (not a dict) in conversation {conversation_id}: {msg_obj}"
                    )
                    continue

                # Collect tool call metadata to attach to next assistant message
                if msg_obj.get("metadata_type") == "tool_calls":
                    tool_calls = msg_obj.get("tool_calls", [])
                    for tc in tool_calls:
                        pending_tool_usage.append({
                            "tool_id": tc.get("id", ""),
                            "tool_name": tc.get("name", "unknown"),
                            "query": self._extract_query_from_tool_call(tc),
                            "details": None,  # Will be filled from tool_result
                        })
                    # Also capture pre-tool thinking content
                    if msg_obj.get("thinking_content"):
                        pending_pre_tool_thinking = msg_obj["thinking_content"]
                        self.logger.debug(
                            f"Captured pre-tool thinking: {len(pending_pre_tool_thinking)} chars"
                        )
                    self.logger.debug(
                        f"Collected {len(tool_calls)} tool calls for next assistant message"
                    )
                    continue

                # Process tool_result to extract details (domains) for display
                if msg_obj.get("metadata_type") == "tool_result":
                    content_text = msg_obj.get("content", "")
                    tool_call_id = msg_obj.get("tool_call_id", "")
                    
                    # Extract URLs using regex (matches http:// and https://)
                    import re
                    urls = re.findall(
                        r'https?://[^\s<>"{}|\\^`\[\]]+', content_text
                    )
                    pending_citations.extend(urls)
                    
                    # Extract domain names for tool details
                    if urls:
                        domains = [url.split("/")[2] for url in urls[:3]]  # Top 3 domains
                        details = ", ".join(domains)
                        # Store details keyed by tool_call_id
                        if tool_call_id:
                            pending_tool_results[tool_call_id] = details
                        # Also update any pending tool_usage entries
                        for tu in pending_tool_usage:
                            if tu.get("tool_id") == tool_call_id:
                                tu["details"] = details
                    
                    self.logger.debug(
                        f"Processed tool result: {tool_call_id}, details: {pending_tool_results.get(tool_call_id)}"
                    )
                    continue

                # Skip tool_calls metadata (already processed above)
                if msg_obj.get("metadata_type") == "tool_calls":
                    continue

                # Also skip by role for backward compatibility
                role = msg_obj.get("role")
                if role in ("tool_calls", "tool_result"):
                    self.logger.debug(
                        f"Skipping tool call message with role: {role}"
                    )
                    continue

                is_bot = role == "assistant"

                # Name extraction logic: prefer message-level, then conversation-level, then default
                if is_bot:
                    name = (
                        msg_obj.get("bot_name")
                        or getattr(conversation, "chatbot_name", None)
                        or "Bot"
                    )
                else:
                    name = (
                        msg_obj.get("user_name")
                        or getattr(conversation, "user_name", None)
                        or "User"
                    )

                # Content extraction logic
                content = msg_obj.get("content")
                if content is None:
                    # Try to extract from blocks if present
                    blocks = msg_obj.get("blocks")
                    if isinstance(blocks, list) and blocks:
                        for block in blocks:
                            if isinstance(block, dict) and "text" in block:
                                content = block["text"]
                                self.logger.debug(
                                    f"Extracted content from blocks: {content[:50]}..."
                                )
                                break
                        if content is None:
                            content = ""
                            self.logger.warning(
                                f"No text found in blocks for message {msg_idx}"
                            )
                    else:
                        content = ""
                        self.logger.warning(
                            f"No blocks found for message {msg_idx}"
                        )
                else:
                    self.logger.debug(
                        f"Content found directly in message {msg_idx}: {content[:50]}..."
                    )

                formatted_msg = {
                    "name": name,
                    "content": content,
                    "is_bot": is_bot,
                    "id": msg_idx,  # Simple index within this loaded history
                }
                
                # Include thinking content for assistant messages
                # Pre-tool thinking goes in pre_tool_thinking, post-tool in thinking_content
                if is_bot:
                    post_tool_thinking = msg_obj.get("thinking_content")
                    if pending_pre_tool_thinking:
                        # Pre-tool thinking always goes in pre_tool_thinking field
                        formatted_msg["pre_tool_thinking"] = pending_pre_tool_thinking
                        pending_pre_tool_thinking = None
                    if post_tool_thinking:
                        # Post-tool thinking goes in thinking_content field
                        formatted_msg["thinking_content"] = post_tool_thinking
                
                # Include tool usage for assistant messages if we have pending tool calls
                if is_bot and pending_tool_usage:
                    formatted_msg["tool_usage"] = pending_tool_usage.copy()
                    pending_tool_usage.clear()

                # Clear pending citations without appending them
                # (sources are shown in tool status details instead)
                if is_bot and pending_citations:
                    pending_citations.clear()

                # Pass through mood/emoji fields if present
                for key in ("bot_mood", "bot_mood_emoji", "user_mood"):
                    if key in msg_obj:
                        formatted_msg[key] = msg_obj[key]
                formatted_messages.append(formatted_msg)
            
            # If there are pending tool calls or thinking that weren't attached to an assistant message
            # (conversation was interrupted), create a synthetic assistant message to display them
            if pending_tool_usage or pending_pre_tool_thinking:
                self.logger.info(
                    f"Creating synthetic assistant message for pending tool data: "
                    f"{len(pending_tool_usage)} tools, "
                    f"thinking={pending_pre_tool_thinking is not None}"
                )
                synthetic_msg = {
                    "name": getattr(conversation, "chatbot_name", None) or "Bot",
                    "content": "",  # Empty content - just showing widgets
                    "is_bot": True,
                    "id": len(formatted_messages),
                }
                if pending_pre_tool_thinking:
                    # Use pre_tool_thinking so it renders BEFORE tool widgets
                    synthetic_msg["pre_tool_thinking"] = pending_pre_tool_thinking
                if pending_tool_usage:
                    synthetic_msg["tool_usage"] = pending_tool_usage.copy()
                formatted_messages.append(synthetic_msg)
            
            self.logger.info(
                f"Successfully loaded {len(formatted_messages)} messages for conversation ID: {conversation_id}"
            )
            return formatted_messages

        except Exception as e:
            self.logger.error(
                f"Error loading conversation history for ID {conversation_id}: {e}",
                exc_info=True,
            )
            return []
