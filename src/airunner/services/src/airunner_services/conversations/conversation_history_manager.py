"""Service-owned conversation history loader and formatter."""

from typing import Any, Dict, List, Optional

from airunner_services.llm.gpt_oss_parser import (
    has_gpt_oss_markup,
    parse_gpt_oss_response,
)
from airunner_services.llm.thinking_parser import (
    normalize_thinking_content,
    strip_stored_thinking_prefix,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.database.models.conversation import Conversation


class ConversationHistoryManager:
    """Handles fetching and formatting of conversation history."""

    def __init__(self) -> None:
        """Initialize one conversation history manager."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def _extract_query_from_tool_call(self, tool_call: Dict[str, Any]) -> str:
        """Extract a user-friendly query string from one tool call."""
        args = tool_call.get("args", {})
        if isinstance(args, dict):
            for key in (
                "query",
                "search_query",
                "prompt",
                "input",
                "question",
            ):
                if key in args:
                    return str(args[key])
            for value in args.values():
                if isinstance(value, str) and value:
                    return value
        return ""

    def get_current_conversation(self) -> Optional[Conversation]:
        """Fetch the current conversation if one exists."""
        conversations = Conversation.objects.filter_by(current=True)
        if len(conversations) == 0:
            self.logger.info("No current conversation found.")
            return None
        self.logger.debug("Fetching the current conversation.")
        try:
            conversation = conversations[0]
            if conversation:
                self.logger.debug(
                    f"Current conversation ID: {conversation.id}"
                )
                return conversation
            self.logger.info("No current conversation found.")
            return None
        except Exception as exc:
            self.logger.error(
                f"Error fetching current conversation: {exc}",
                exc_info=True,
            )
            return None

    def get_most_recent_conversation_id(self) -> Optional[int]:
        """Fetch the most recent conversation id if one exists."""
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
        except Exception as exc:
            self.logger.error(
                f"Error fetching most recent conversation ID: {exc}",
                exc_info=True,
            )
            return None

    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return serialized conversation metadata for service consumers."""
        conversations = Conversation.objects.filter(Conversation.id >= 1) or []
        ordered = sorted(
            conversations,
            key=lambda item: getattr(item, "id", 0),
            reverse=True,
        )
        if limit > 0:
            ordered = ordered[:limit]
        return [self._conversation_payload(item) for item in ordered]

    def get_conversation_session(
        self,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
        mark_current: bool = False,
    ) -> Dict[str, Any]:
        """Return one serialized conversation plus formatted messages."""
        conversation = self._resolve_conversation(conversation_id)
        if conversation is None:
            return {
                "conversation": None,
                "conversation_id": None,
                "messages": [],
            }

        if mark_current:
            Conversation.make_current(conversation.id)
            conversation.current = True

        messages = self.load_conversation_history(
            conversation=conversation,
            max_messages=max_messages,
        )
        return {
            "conversation": self._conversation_payload(conversation),
            "conversation_id": conversation.id,
            "messages": messages,
        }

    def summarize_conversation(
        self,
        conversation_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return one persisted or generated summary for a conversation."""
        conversation = Conversation.objects.filter_by_first(id=conversation_id)
        if conversation is None:
            return None
        return {
            "conversation_id": conversation_id,
            "summary": self._conversation_summary(conversation),
        }

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete one conversation from persistent storage."""
        conversation = Conversation.objects.filter_by_first(id=conversation_id)
        if conversation is None:
            return False
        Conversation.delete(conversation_id)
        return True

    def _resolve_conversation(
        self,
        conversation_id: Optional[int],
    ) -> Optional[Conversation]:
        """Resolve one conversation by id or current/most-recent fallback."""
        if conversation_id is not None:
            return Conversation.objects.filter_by_first(id=conversation_id)

        current = self.get_current_conversation()
        if current is not None:
            return current
        return Conversation.most_recent()

    def _conversation_payload(
        self,
        conversation: Conversation,
    ) -> Dict[str, Any]:
        """Serialize one conversation into JSON-safe metadata."""
        raw_messages = getattr(conversation, "value", None)
        if not isinstance(raw_messages, list):
            raw_messages = []

        return {
            "id": getattr(conversation, "id", None),
            "title": str(getattr(conversation, "title", "") or ""),
            "summary": self._conversation_summary(conversation),
            "current": bool(getattr(conversation, "current", False)),
            "timestamp": self._serialize_timestamp(
                getattr(conversation, "timestamp", None)
            ),
            "chatbot_id": getattr(conversation, "chatbot_id", None),
            "chatbot_name": str(
                getattr(conversation, "chatbot_name", "") or ""
            ),
            "user_id": getattr(conversation, "user_id", None),
            "user_name": str(getattr(conversation, "user_name", "") or ""),
            "message_count": len(raw_messages),
            "user_data": dict(getattr(conversation, "user_data", None) or {}),
        }

    def _conversation_summary(self, conversation: Conversation) -> str:
        """Return one cached or generated conversation summary."""
        summary = str(getattr(conversation, "summary", "") or "").strip()
        if summary:
            return summary

        try:
            summary = str(conversation.summarize() or "").strip()
        except Exception as exc:
            self.logger.warning(
                "Failed to summarize conversation %s: %s",
                getattr(conversation, "id", None),
                exc,
            )
            return ""

        if not summary:
            return ""

        try:
            Conversation.objects.update(conversation.id, summary=summary)
        except Exception as exc:
            self.logger.warning(
                "Failed to persist summary for conversation %s: %s",
                getattr(conversation, "id", None),
                exc,
            )
        conversation.summary = summary
        return summary

    @staticmethod
    def _serialize_timestamp(timestamp: Any) -> str:
        """Return one string representation for a conversation timestamp."""
        if timestamp is None:
            return ""
        formatter = getattr(timestamp, "isoformat", None)
        if callable(formatter):
            try:
                return formatter()
            except Exception:
                pass
        return str(timestamp)

    def load_conversation_history(
        self,
        conversation: Optional[Conversation] = None,
        conversation_id: Optional[int] = None,
        max_messages: int = 50,
    ) -> List[Dict[str, Any]]:
        """Load and format one conversation history for display."""
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
            "Loading conversation history for ID: %s (max: %s)",
            getattr(conversation, "id", None),
            max_messages,
        )
        conversation_id = getattr(conversation, "id", None)
        try:
            raw_messages = getattr(conversation, "value", None)
            if not isinstance(raw_messages, list):
                self.logger.warning(
                    "Conversation %s has invalid message data (not a list): %s",
                    conversation_id,
                    type(raw_messages),
                )
                return []
            if not raw_messages:
                self.logger.debug(f"Conversation {conversation_id} is empty.")
                return []

            if len(raw_messages) > max_messages:
                raw_messages = raw_messages[-max_messages:]

            pending_citations: List[str] = []
            pending_tool_usage: List[Dict[str, Any]] = []
            pending_tool_results: Dict[str, str] = {}
            pending_pre_tool_thinking: Optional[str] = None

            formatted_messages: List[Dict[str, Any]] = []
            for msg_idx, msg_obj in enumerate(raw_messages):
                if not isinstance(msg_obj, dict):
                    self.logger.warning(
                        "Skipping invalid message object (not a dict) in "
                        "conversation %s: %s",
                        conversation_id,
                        msg_obj,
                    )
                    continue

                if msg_obj.get("metadata_type") == "tool_calls":
                    tool_calls = msg_obj.get("tool_calls", [])
                    for tool_call in tool_calls:
                        pending_tool_usage.append(
                            {
                                "tool_id": tool_call.get("id", ""),
                                "tool_name": tool_call.get(
                                    "name", "unknown"
                                ),
                                "query": self._extract_query_from_tool_call(
                                    tool_call
                                ),
                                "details": None,
                            }
                        )
                    pending_pre_tool_thinking = normalize_thinking_content(
                        msg_obj.get("thinking_content")
                    )
                    if pending_pre_tool_thinking:
                        self.logger.debug(
                            "Captured pre-tool thinking: %s chars",
                            len(pending_pre_tool_thinking),
                        )
                    self.logger.debug(
                        "Collected %s tool calls for next assistant "
                        "message",
                        len(tool_calls),
                    )
                    continue

                if msg_obj.get("metadata_type") == "tool_result":
                    content_text = msg_obj.get("content", "")
                    tool_call_id = msg_obj.get("tool_call_id", "")

                    import re

                    urls = re.findall(
                        r'https?://[^\s<>"{}|\\^`\[\]]+',
                        content_text,
                    )
                    pending_citations.extend(urls)

                    if urls:
                        domains = [url.split("/")[2] for url in urls[:3]]
                        details = ", ".join(domains)
                        if tool_call_id:
                            pending_tool_results[tool_call_id] = details
                        for tool_usage in pending_tool_usage:
                            if tool_usage.get("tool_id") == tool_call_id:
                                tool_usage["details"] = details

                    self.logger.debug(
                        "Processed tool result: %s, details: %s",
                        tool_call_id,
                        pending_tool_results.get(tool_call_id),
                    )
                    continue

                if msg_obj.get("metadata_type") == "tool_calls":
                    continue

                role = msg_obj.get("role")
                if role in ("tool_calls", "tool_result"):
                    self.logger.debug(
                        f"Skipping tool call message with role: {role}"
                    )
                    continue

                is_bot = role == "assistant"
                post_tool_thinking = normalize_thinking_content(
                    msg_obj.get("thinking_content")
                )

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

                content = msg_obj.get("content")
                if content is None:
                    blocks = msg_obj.get("blocks")
                    if isinstance(blocks, list) and blocks:
                        for block in blocks:
                            if isinstance(block, dict) and "text" in block:
                                content = block["text"]
                                self.logger.debug(
                                    "Extracted content from blocks: %s...",
                                    content[:50],
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
                        "Content found directly in message %s: %s...",
                        msg_idx,
                        content[:50],
                    )

                if is_bot:
                    if has_gpt_oss_markup(content):
                        parsed = parse_gpt_oss_response(content)
                        content = parsed.content or content
                        parsed_thinking = normalize_thinking_content(
                            parsed.thinking_content
                        )
                        if parsed_thinking and not post_tool_thinking:
                            post_tool_thinking = parsed_thinking
                    content = strip_stored_thinking_prefix(
                        content,
                        post_tool_thinking,
                    )

                formatted_msg = {
                    "name": name,
                    "content": content,
                    "is_bot": is_bot,
                    "id": msg_idx,
                }

                if is_bot:
                    if pending_pre_tool_thinking:
                        formatted_msg[
                            "pre_tool_thinking"
                        ] = pending_pre_tool_thinking
                        pending_pre_tool_thinking = None
                    if post_tool_thinking:
                        formatted_msg["thinking_content"] = post_tool_thinking

                if is_bot and pending_tool_usage:
                    formatted_msg["tool_usage"] = pending_tool_usage.copy()
                    pending_tool_usage.clear()

                if is_bot and pending_citations:
                    pending_citations.clear()

                for key in ("bot_mood", "bot_mood_emoji", "user_mood"):
                    if key in msg_obj:
                        formatted_msg[key] = msg_obj[key]
                formatted_messages.append(formatted_msg)

            if pending_tool_usage or pending_pre_tool_thinking:
                self.logger.info(
                    "Creating synthetic assistant message for pending tool "
                    "data: %s tools, thinking=%s",
                    len(pending_tool_usage),
                    pending_pre_tool_thinking is not None,
                )
                synthetic_msg = {
                    "name": getattr(conversation, "chatbot_name", None)
                    or "Bot",
                    "content": "",
                    "is_bot": True,
                    "id": len(formatted_messages),
                }
                if pending_pre_tool_thinking:
                    synthetic_msg[
                        "pre_tool_thinking"
                    ] = pending_pre_tool_thinking
                if pending_tool_usage:
                    synthetic_msg["tool_usage"] = pending_tool_usage.copy()
                formatted_messages.append(synthetic_msg)

            self.logger.info(
                "Successfully loaded %s messages for conversation ID: %s",
                len(formatted_messages),
                conversation_id,
            )
            return formatted_messages

        except Exception as exc:
            self.logger.error(
                f"Error loading conversation history for ID {conversation_id}: {exc}",
                exc_info=True,
            )
            return []
