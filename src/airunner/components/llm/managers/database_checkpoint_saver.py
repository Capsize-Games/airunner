"""Custom LangGraph checkpointer that persists to the Conversation database."""

import logging
import json
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

from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.managers.database_chat_message_history import (
    DatabaseChatMessageHistory,
)


class DatabaseCheckpointSaver(BaseCheckpointSaver):
    """LangGraph checkpoint saver that persists conversation state to database.

    This integrates LangGraph's checkpointing system with AI Runner's Conversation
    model, ensuring conversation state is properly saved and can be restored.
    """

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
            # Extract messages from checkpoint
            if "messages" in checkpoint.get("channel_values", {}):
                messages = checkpoint["channel_values"]["messages"]

                # Only update if message count changed or content differs
                existing_messages = self.message_history.messages
                if len(messages) != len(existing_messages):
                    # Clear and re-add all messages
                    self.message_history.clear()
                    self.message_history.add_messages(messages)
                    self.logger.debug(
                        f"Saved checkpoint with {len(messages)} messages to conversation {self.message_history.conversation_id}"
                    )
                else:
                    self.logger.debug(
                        f"Skipping checkpoint save - message count unchanged ({len(messages)})"
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
            # Load messages from database
            messages = self.message_history.messages

            if not messages:
                return None

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
        pass

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
