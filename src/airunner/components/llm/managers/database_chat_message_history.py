"""LangChain message history implementation that persists to the Conversation database."""

from typing import List, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)

from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.utils.thinking_parser import strip_thinking_tags, extract_thinking_and_response
from airunner.utils.application.get_logger import get_logger


class DatabaseChatMessageHistory(BaseChatMessageHistory):
    """Chat message history that stores messages in the Conversation database.

    This class integrates LangChain's memory system with AI Runner's Conversation
    model, ensuring that all chat messages are properly persisted to the database
    and can be loaded later.

    Ephemeral Mode:
        When ephemeral=True, messages are kept in memory only and never saved to
        the database. This is useful for:
        - Headless API requests that shouldn't pollute conversation history
        - Batch processing tasks (e.g., book classification)
        - Temporary analysis or classification tasks
        - Any operation that should leave no trace in conversation history
    """

    def __init__(
        self, conversation_id: Optional[int] = None, ephemeral: bool = False
    ):
        """Initialize the database chat message history.

        Args:
            conversation_id: Optional conversation ID to load. If None, will use
                           or create the current conversation.
            ephemeral: If True, messages won't be saved to database (memory-only)
        """
        self.logger = get_logger(self.__class__.__name__)
        self.conversation_id = conversation_id
        self.ephemeral = ephemeral
        self._conversation = None
        self._ephemeral_messages = []  # In-memory storage for ephemeral mode

        if not ephemeral:
            self._load_conversation()

    def _load_conversation(self) -> None:
        """Load the conversation from database or create a new one."""
        try:
            if self.conversation_id:
                # Load specific conversation
                self._conversation = Conversation.objects.get(
                    self.conversation_id
                )
            else:
                # Get or create current conversation
                conversations = Conversation.objects.filter_by(current=True)
                if conversations:
                    self._conversation = conversations[0]
                else:
                    # Create new conversation
                    self._conversation = Conversation.create()
                    if self._conversation:
                        self.conversation_id = self._conversation.id
                        Conversation.make_current(self.conversation_id)

            if self._conversation:
                self.conversation_id = self._conversation.id
                self.logger.info(
                    f"Loaded conversation ID: {self.conversation_id}"
                )
            else:
                self.logger.warning("Failed to load or create conversation")

        except Exception as e:
            self.logger.error(
                f"Error loading conversation: {e}", exc_info=True
            )

    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve all messages from the conversation.

        Returns:
            List of LangChain BaseMessage objects (excludes tool call metadata)
        """
        # In ephemeral mode, return in-memory messages
        if self.ephemeral:
            return self._ephemeral_messages.copy()

        if not self._conversation:
            return []

        try:
            # Refresh conversation from database
            self._conversation = Conversation.objects.get(self.conversation_id)
            conversation_value = self._conversation.value or []

            # Convert from database format to LangChain messages
            langchain_messages = []
            for msg in conversation_value:
                # Skip metadata entries (tool calls and tool results)
                # These are stored for debugging but not sent to the LLM
                if msg.get("metadata_type") in ("tool_calls", "tool_result"):
                    continue

                role = msg.get("role", "user")
                content = msg.get("content", "")

                # Map roles to LangChain message types
                if role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif role in ("assistant", "bot"):
                    langchain_messages.append(AIMessage(content=content))
                elif role == "system":
                    langchain_messages.append(SystemMessage(content=content))

            return langchain_messages

        except Exception as e:
            self.logger.error(f"Error retrieving messages: {e}", exc_info=True)
            return []

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation.

        Args:
            message: LangChain message to add
        """
        # In ephemeral mode, store in memory only
        if self.ephemeral:
            self._ephemeral_messages.append(message)
            return

        if not self._conversation:
            self.logger.error("Cannot add message: no conversation loaded")
            return

        try:
            import datetime
            
            # CRITICAL: Reload conversation from database to get latest state
            # This ensures deduplication checks against the most current data
            self._load_conversation()

            # Track tool calls and tool messages for debugging, but store them separately
            # These won't appear as regular conversation messages but will be logged

            # Handle ToolMessages (results from tool execution)
            if message.__class__.__name__ == "ToolMessage":
                tool_call_id = getattr(message, "tool_call_id", None)
                self.logger.debug(
                    f"Tool result: {message.content[:100]}... "
                    f"(tool_call_id: {tool_call_id or 'unknown'})"
                )
                
                # DEDUPLICATION: Check if tool_result with same tool_call_id already exists
                if self._conversation.value and tool_call_id:
                    for existing in self._conversation.value:
                        if (existing.get("metadata_type") == "tool_result" and 
                            existing.get("tool_call_id") == tool_call_id):
                            self.logger.debug(
                                f"Skipping duplicate tool_result for tool_call_id: {tool_call_id}"
                            )
                            return
                
                # Store tool result in a separate metadata entry
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                tool_result_dict = {
                    "role": "tool_result",
                    "name": "Tool Result",
                    "content": message.content,
                    "timestamp": now,
                    "blocks": [
                        {"block_type": "text", "text": message.content}
                    ],
                    "tool_call_id": tool_call_id,
                    "metadata_type": "tool_result",  # Mark as metadata for filtering
                }
                if self._conversation.value is None:
                    self._conversation.value = []
                self._conversation.value.append(tool_result_dict)
                Conversation.objects.update(
                    self.conversation_id, value=self._conversation.value
                )
                return

            # Handle AIMessages with tool_calls (LLM requesting tool execution)
            if (
                isinstance(message, AIMessage)
                and hasattr(message, "tool_calls")
                and message.tool_calls
            ):
                self.logger.debug(
                    f"Tool calls requested: {[tc.get('name', 'unknown') for tc in message.tool_calls]}"
                )
                
                # DEDUPLICATION: Check if tool_calls with same IDs already exist
                # Get all tool_call IDs from the incoming message
                incoming_tool_ids = set(
                    tc.get("id") for tc in message.tool_calls if tc.get("id")
                )
                if self._conversation.value and incoming_tool_ids:
                    for existing in self._conversation.value:
                        if existing.get("metadata_type") == "tool_calls":
                            existing_tool_calls = existing.get("tool_calls", [])
                            for tc in existing_tool_calls:
                                if tc.get("id") in incoming_tool_ids:
                                    self.logger.debug(
                                        f"Skipping duplicate tool_calls - tool_call_id already exists: {tc.get('id')}"
                                    )
                                    return
                
                # Extract thinking content from the AIMessage that has tool_calls
                # This captures the "thinking before tool use" phase
                thinking_content = None
                if hasattr(message, "additional_kwargs") and message.additional_kwargs:
                    thinking_content = message.additional_kwargs.get("thinking_content")
                if not thinking_content and message.content:
                    thinking_content, _ = extract_thinking_and_response(message.content)
                
                # Store tool call request in metadata
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                tool_calls_dict = {
                    "role": "tool_calls",
                    "name": "Tool Planning",
                    "content": f"Requested {len(message.tool_calls)} tool(s): "
                    + ", ".join(
                        [
                            tc.get("name", "unknown")
                            for tc in message.tool_calls
                        ]
                    ),
                    "timestamp": now,
                    "blocks": [
                        {
                            "block_type": "text",
                            "text": f"Tool calls: {message.tool_calls}",
                        }
                    ],
                    "tool_calls": message.tool_calls,  # Store actual tool call data
                    "metadata_type": "tool_calls",  # Mark as metadata for filtering
                }
                
                # Store thinking content if present (pre-tool thinking)
                if thinking_content:
                    tool_calls_dict["thinking_content"] = thinking_content
                    self.logger.debug(f"[THINKING SAVE] Saved pre-tool thinking: {len(thinking_content)} chars")
                
                if self._conversation.value is None:
                    self._conversation.value = []
                self._conversation.value.append(tool_calls_dict)
                Conversation.objects.update(
                    self.conversation_id, value=self._conversation.value
                )
                return

            # Convert LangChain message to database format
            role = "user"
            name = "User"

            if isinstance(message, HumanMessage):
                role = "user"
                name = getattr(self._conversation, "user_name", "User")
            elif isinstance(message, AIMessage):
                role = "assistant"
                name = getattr(self._conversation, "chatbot_name", "Assistant")
            elif isinstance(message, SystemMessage):
                role = "system"
                name = "System"

            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Extract thinking content for AI messages
            # First check additional_kwargs (from streaming), then try to extract from content
            content = message.content
            thinking_content = None
            if isinstance(message, AIMessage):
                # Check if thinking_content was stored in additional_kwargs during streaming
                if hasattr(message, "additional_kwargs") and message.additional_kwargs:
                    thinking_content = message.additional_kwargs.get("thinking_content")
                    self.logger.debug(f"[THINKING SAVE] Found thinking_content in additional_kwargs: {bool(thinking_content)}")
                
                # If not found, try to extract from content (for non-streaming or fallback)
                if not thinking_content:
                    thinking_content, content = extract_thinking_and_response(content)
                    self.logger.debug(f"[THINKING SAVE] Extracted from content: {bool(thinking_content)}")
                
                self.logger.debug(f"[THINKING SAVE] Final thinking_content length: {len(thinking_content) if thinking_content else 0}")

            message_dict = {
                "role": role,
                "name": name,
                "content": content,
                "timestamp": now,
                "blocks": [{"block_type": "text", "text": content}],
            }
            
            # Add thinking content if present
            if thinking_content:
                message_dict["thinking_content"] = thinking_content

            # Add metadata if present
            if (
                hasattr(message, "additional_kwargs")
                and message.additional_kwargs
            ):
                message_dict.update(message.additional_kwargs)

            # DEDUPLICATION: Check for duplicate user/assistant messages
            # Skip if the same role + content already exists as the last message of that role
            if self._conversation.value:
                # Find the last message with the same role
                for existing in reversed(self._conversation.value):
                    if existing.get("role") == role:
                        existing_content = existing.get("content", "")
                        if existing_content == content:
                            self.logger.debug(
                                f"Skipping duplicate {role} message: {content[:50]}..."
                            )
                            return
                        # Only compare against the most recent message of this role
                        break

            # Append to conversation
            if self._conversation.value is None:
                self._conversation.value = []
            self._conversation.value.append(message_dict)

            # Save to database
            Conversation.objects.update(
                self.conversation_id, value=self._conversation.value
            )

        except Exception as e:
            self.logger.error(f"Error adding message: {e}", exc_info=True)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add multiple messages to the conversation.

        Args:
            messages: List of LangChain messages to add
        """
        for message in messages:
            self.add_message(message)

    def clear(self) -> None:
        """Clear all messages from the conversation."""
        if not self._conversation:
            return

        try:
            self._conversation.value = []
            Conversation.objects.update(self.conversation_id, value=[])
            self.logger.info(f"Cleared conversation {self.conversation_id}")

        except Exception as e:
            self.logger.error(
                f"Error clearing conversation: {e}", exc_info=True
            )

    def get_tool_call_metadata(self) -> List[dict]:
        """Retrieve tool call metadata for debugging.

        Returns:
            List of dicts containing tool call requests and results
        """
        if not self._conversation:
            return []

        try:
            # Refresh conversation from database
            self._conversation = Conversation.objects.get(self.conversation_id)
            conversation_value = self._conversation.value or []

            # Extract only metadata entries
            metadata = []
            for msg in conversation_value:
                if msg.get("metadata_type") in ("tool_calls", "tool_result"):
                    metadata.append(msg)

            return metadata

        except Exception as e:
            self.logger.error(
                f"Error retrieving tool call metadata: {e}", exc_info=True
            )
            return []
