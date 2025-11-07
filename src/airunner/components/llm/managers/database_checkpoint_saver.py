"""Custom LangGraph checkpointer that persists to the Conversation database."""

import logging
import uuid
from typing import Optional, Dict, Any, Iterator, Tuple
from collections.abc import Sequence

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langchain_core.runnables import RunnableConfig

from airunner.components.llm.managers.database_chat_message_history import (
    DatabaseChatMessageHistory,
)


class DatabaseCheckpointSaver(BaseCheckpointSaver):
    """LangGraph checkpoint saver that persists conversation state to database.

    This integrates LangGraph's checkpointing system with AI Runner's Conversation
    model, ensuring conversation state is properly saved and can be restored.
    """

    # CLASS-LEVEL storage for checkpoint state (shared across all instances)
    # This ensures checkpoint state persists even when new instances are created
    _checkpoint_state: Dict[str, Any] = {}

    def __init__(self, conversation_id: Optional[int] = None):
        """Initialize the database checkpoint saver.

        Args:
            conversation_id: Optional conversation ID to use. If None, will use
                           the current conversation.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.conversation_id = conversation_id
        self.message_history = DatabaseChatMessageHistory(conversation_id)

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None,
    ) -> RunnableConfig:
        """Save a checkpoint to the database.

        Args:
            config: Runtime configuration
            checkpoint: Checkpoint data to save
            metadata: Checkpoint metadata
            new_versions: Optional version information

        Returns:
            Updated configuration with checkpoint ID
        """
        try:
            self.logger.info(
                f"🔵 DatabaseCheckpointSaver.put() called for conversation {self.conversation_id}"
            )

            # Extract messages from checkpoint
            if "messages" in checkpoint.get("channel_values", {}):
                messages = checkpoint["channel_values"]["messages"]

                self.logger.info(f"🔵 Checkpoint has {len(messages)} messages")
                if messages:
                    last_msg = messages[-1]
                    last_msg_type = type(last_msg).__name__
                    last_msg_content = getattr(last_msg, "content", "")[:100]
                    self.logger.info(
                        f"🔵 Last message type: {last_msg_type}, content preview: '{last_msg_content}'"
                    )

                # Check if we need to update
                existing_messages = self.message_history.messages
                needs_update = False

                if len(messages) != len(existing_messages):
                    needs_update = True
                    self.logger.info(
                        f"🟢 Message count changed: {len(existing_messages)} -> {len(messages)}"
                    )
                elif len(messages) > 0 and len(existing_messages) > 0:
                    # Same count - check if last message content differs
                    # This handles cases where we replace messages (e.g., forced responses)
                    last_new = messages[-1]
                    last_existing = existing_messages[-1]

                    new_content = getattr(last_new, "content", "")
                    existing_content = getattr(last_existing, "content", "")

                    if new_content != existing_content:
                        needs_update = True
                        self.logger.info(
                            f"🟢 Last message content changed (preview): '{existing_content[:50]}...' -> '{new_content[:50]}...'"
                        )

                if needs_update:
                    # Clear and re-add all messages
                    self.logger.info(
                        "🟢 Clearing and re-adding messages to database..."
                    )
                    self.message_history.clear()
                    self.message_history.add_messages(messages)
                    self.logger.info(
                        f"✅ Saved checkpoint with {len(messages)} messages to conversation {self.message_history.conversation_id}"
                    )

                    # Store full checkpoint state (including ToolMessages)
                    # Update cache with ALL messages (including ToolMessages)
                # CRITICAL: Use conversation_id as thread_id to prevent contamination
                # between different conversations (e.g., in tests)
                if messages:
                    thread_id = str(self.message_history.conversation_id)
                    self._checkpoint_state[thread_id] = {
                        "checkpoint": checkpoint,
                        "metadata": metadata,
                        "messages": messages,
                    }
                    self.logger.info(
                        f"💾 Stored full checkpoint state with {len(messages)} messages for thread {thread_id}"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Skipping checkpoint save - no changes detected ({len(messages)} messages)"
                    )

            # Generate a proper UUID for the checkpoint if not present
            checkpoint_id = checkpoint.get("id")
            if not checkpoint_id:
                checkpoint_id = str(uuid.uuid4())

            # Return config with thread info
            return {
                "configurable": {
                    "thread_id": str(self.message_history.conversation_id),
                    "checkpoint_id": checkpoint_id,
                }
            }

        except Exception as e:
            self.logger.error(f"Error saving checkpoint: {e}", exc_info=True)
            return config

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Retrieve a checkpoint from the database.

        Args:
            config: Runtime configuration

        Returns:
            Checkpoint tuple or None if not found
        """
        try:
            # First, try to get from in-memory checkpoint state
            thread_id = config.get("configurable", {}).get("thread_id")
            if thread_id and thread_id in self._checkpoint_state:
                state = self._checkpoint_state[thread_id]
                self.logger.info(
                    f"📥 Loaded checkpoint from memory for thread {thread_id} with {len(state['messages'])} messages (includes ToolMessages)"
                )
                return CheckpointTuple(
                    config=config,
                    checkpoint=state["checkpoint"],
                    metadata=state["metadata"],
                    parent_config=None,
                )

            # Fallback: Load from database (may not have ToolMessages)
            messages = self.message_history.messages

            if not messages:
                self.logger.info("📥 No checkpoint found - starting fresh")
                return None

            self.logger.info(
                f"📥 Loaded checkpoint from DATABASE for thread {thread_id} with {len(messages)} messages (ToolMessages filtered out)"
            )

            # Build checkpoint with proper UUID
            checkpoint = Checkpoint(
                v=1,
                id=str(uuid.uuid4()),
                ts="",
                channel_values={
                    "messages": messages,
                },
                channel_versions={},
                versions_seen={},
            )

            metadata = CheckpointMetadata(
                source="database",
                step=len(messages),
                writes={},
            )

            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=None,
            )

        except Exception as e:
            self.logger.error(
                f"Error retrieving checkpoint: {e}", exc_info=True
            )
            return None

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Store intermediate writes from graph execution.

        Args:
            config: Runtime configuration
            writes: Sequence of (channel, value) writes to store
            task_id: Unique identifier for the task
        """
        # For our simple implementation, we don't need to store intermediate writes
        # The final state will be saved via put()

    def list(
        self,
        config: RunnableConfig,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints from the database.

        Args:
            config: Runtime configuration
            filter: Optional filter criteria
            before: Optional config to list checkpoints before
            limit: Optional limit on number of checkpoints

        Yields:
            Checkpoint tuples
        """
        # For now, just return the current checkpoint if it exists
        current = self.get_tuple(config)
        if current:
            yield current

    def clear_checkpoints(self) -> None:
        """Clear all checkpoint state.

        This removes all in-memory checkpoint state from the class-level
        _checkpoint_state dictionary, forcing a fresh start for the workflow.

        CRITICAL: This is needed to prevent checkpoint contamination between
        tests or when resetting conversation memory.
        """
        # Clear the class-level checkpoint state dictionary
        DatabaseCheckpointSaver._checkpoint_state.clear()
        self.logger.info("Cleared all LangGraph checkpoint state")

        # Also clear message history for completeness
        self.message_history.clear()
        self.logger.info(
            f"Cleared message history for conversation {self.conversation_id}"
        )
