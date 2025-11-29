"""Custom LangGraph checkpointer that persists to the Conversation database."""

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
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class DatabaseCheckpointSaver(BaseCheckpointSaver):
    """LangGraph checkpoint saver that persists conversation state to database.

    This integrates LangGraph's checkpointing system with AI Runner's Conversation
    model, ensuring conversation state is properly saved and can be restored.
    """

    # CLASS-LEVEL storage for checkpoint state (shared across all instances)
    # This ensures checkpoint state persists even when new instances are created
    _checkpoint_state: Dict[str, Any] = {}
    _stateless_mode: bool = (
        False  # New: disable checkpoint persistence globally
    )

    def __init__(
        self,
        conversation_id: Optional[int] = None,
        stateless: bool = False,
        ephemeral: bool = False,
    ):
        """Initialize the database checkpoint saver.

        Args:
            conversation_id: Optional conversation ID to use. If None, will use
                           the current conversation.
            stateless: If True, disable checkpoint persistence (for independent requests)
            ephemeral: If True, disable conversation history persistence (no DB writes)
        """
        super().__init__()
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self.conversation_id = conversation_id
        self.ephemeral = ephemeral
        self.message_history = DatabaseChatMessageHistory(
            conversation_id, ephemeral=ephemeral
        )
        self.stateless = stateless or DatabaseCheckpointSaver._stateless_mode

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
            # In stateless mode, don't persist checkpoints
            if self.stateless:
                return {
                    "configurable": {
                        "thread_id": str(
                            uuid.uuid4()
                        ),  # Random thread ID each time
                        "checkpoint_id": str(uuid.uuid4()),
                    }
                }

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

                # CRITICAL FIX: Only append NEW messages, don't clear existing ones.
                # The database stores rich message format (blocks, metadata, etc.)
                # that gets lost when we clear and re-save LangChain messages.
                # 
                # Strategy: Count existing LangChain-compatible messages (user/assistant)
                # and only add messages beyond that count.
                
                # Refresh conversation from database to ensure we have latest state
                self.message_history._load_conversation()
                raw_conv = self.message_history._conversation
                existing_value = raw_conv.value if raw_conv and raw_conv.value else []
                
                # Count only user/assistant messages (what LangGraph sees)
                existing_langchain_count = sum(
                    1 for msg in existing_value 
                    if msg.get("role") in ("user", "assistant", "bot")
                    and msg.get("metadata_type") not in ("tool_calls", "tool_result")
                )
                checkpoint_count = len(messages)
                
                self.logger.info(
                    f"🔵 Comparing: DB has {existing_langchain_count} user/assistant msgs, "
                    f"checkpoint has {checkpoint_count} messages"
                )
                
                # Only add messages that are NEW (beyond what's already in DB)
                if checkpoint_count > existing_langchain_count:
                    new_messages = messages[existing_langchain_count:]
                    self.logger.info(
                        f"🔵 Adding {len(new_messages)} new messages to conversation"
                    )
                    for msg in new_messages:
                        self.message_history.add_message(msg)
                    self.logger.info(
                        f"✅ Appended {len(new_messages)} new messages to conversation {self.message_history.conversation_id}"
                    )
                elif checkpoint_count == existing_langchain_count:
                    self.logger.info(
                        f"✅ No new messages to save (checkpoint matches DB count)"
                    )
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
        """Fetch a checkpoint tuple using the given configuration.

        Args:
            config: Configuration specifying which checkpoint to retrieve.

        Returns:
            The requested checkpoint tuple, or None if not found.
        """
        return self.get(config)

    def get(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Retrieve a checkpoint from the database.

        Args:
            config: Runtime configuration

        Returns:
        Checkpoint tuple or None if not found
        """
        try:
            # In stateless mode, always return None (fresh start)
            if self.stateless:
                self.logger.debug(
                    "Stateless mode: returning None (no checkpoint restoration)"
                )
                return None

            # First, try to get from in-memory checkpoint state
            thread_id = config.get("configurable", {}).get("thread_id")

            # DEBUG: Write to file
            import sys

            with open("/tmp/checkpoint_debug.log", "a") as f:
                f.write(
                    f"[GET] thread_id={thread_id}, conv_id={self.conversation_id}, "
                    f"checkpoint_keys={list(self._checkpoint_state.keys())}\n"
                )
                sys.stdout.flush()

            if thread_id and thread_id in self._checkpoint_state:
                state = self._checkpoint_state[thread_id]
                with open("/tmp/checkpoint_debug.log", "a") as f:
                    f.write(
                        f"[GET] ✅ FOUND in memory: {len(state['messages'])} messages\n"
                    )
                return CheckpointTuple(
                    config=config,
                    checkpoint=state["checkpoint"],
                    metadata=state["metadata"],
                    parent_config=None,
                )

            # Fallback: Load from database (may not have ToolMessages)
            messages = self.message_history.messages
            with open("/tmp/checkpoint_debug.log", "a") as f:
                f.write(
                    f"[GET] DB has {len(messages)} messages for conv {self.conversation_id}\n"
                )

            if not messages:
                with open("/tmp/checkpoint_debug.log", "a") as f:
                    f.write(f"[GET] ❌ No messages - starting fresh\n")
                return None

            with open("/tmp/checkpoint_debug.log", "a") as f:
                f.write(
                    f"[GET] ✅ Building checkpoint from DB: {len(messages)} messages\n"
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

    def clear_checkpoints(self, clear_history: bool = True) -> None:
        """Clear checkpoint cache and optionally wipe stored history.

        Args:
            clear_history: When True (default), also clear the persisted
                conversation transcript. Set to False when you only need to
                drop LangGraph's cached checkpoints but want to keep the
                existing database history intact.
        """
        # CRITICAL FIX: Only clear checkpoint state for THIS conversation's thread,
        # not ALL conversations. The old code was wiping all checkpoint state globally.
        thread_id = str(self.conversation_id) if self.conversation_id else None
        if thread_id and thread_id in DatabaseCheckpointSaver._checkpoint_state:
            del DatabaseCheckpointSaver._checkpoint_state[thread_id]
            self.logger.info(f"Cleared checkpoint state for thread {thread_id}")
        else:
            self.logger.info(f"No checkpoint state to clear for thread {thread_id}")

        if clear_history:
            self.message_history.clear()
            self.logger.info(
                f"Cleared message history for conversation {self.conversation_id}"
            )

    def clear_thread(self, thread_id: str) -> None:
        """Clear checkpoint state for a specific thread.

        This removes checkpoint state for a single thread, useful for
        cleaning up between independent operations (e.g., classifying different books).

        Args:
            thread_id: The thread ID to clear
        """
        if thread_id in DatabaseCheckpointSaver._checkpoint_state:
            del DatabaseCheckpointSaver._checkpoint_state[thread_id]
            self.logger.info(
                f"Cleared checkpoint state for thread {thread_id}"
            )

    @classmethod
    def clear_all_checkpoint_state(cls) -> None:
        """Clear ALL checkpoint state globally. Use only for testing cleanup.
        
        WARNING: This clears checkpoint state for ALL conversations, not just one.
        Use clear_checkpoints() for normal per-conversation cleanup.
        """
        cls._checkpoint_state.clear()
        get_logger(__name__, AIRUNNER_LOG_LEVEL).info(
            "Cleared ALL global checkpoint state (test cleanup)"
        )

    @classmethod
    def set_stateless_mode(cls, enabled: bool) -> None:
        """Enable or disable stateless mode globally.

        When enabled, all DatabaseCheckpointSaver instances will not persist
        checkpoints, making each operation completely independent.

        Args:
            enabled: Whether to enable stateless mode
        """
        cls._stateless_mode = enabled
        get_logger(__name__, AIRUNNER_LOG_LEVEL).info(
            f"Stateless mode: {enabled}"
        )
