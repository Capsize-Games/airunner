"""Custom LangGraph checkpointer that persists to the Conversation database."""

import uuid
from collections import OrderedDict
from typing import Optional, Dict, Any, Iterator, List, Tuple
from collections.abc import Sequence

from langchain_core.messages import BaseMessage
from langchain_core.messages.utils import count_tokens_approximately

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langchain_core.runnables import RunnableConfig

from airunner_services.llm.managers.database_chat_message_history import (
    DatabaseChatMessageHistory,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


_CHECKPOINT_STATE_MAX_SIZE = 100


class DatabaseCheckpointSaver(BaseCheckpointSaver):
    """LangGraph checkpoint saver that persists conversation state to database.

    This integrates LangGraph's checkpointing system with AI Runner's Conversation
    model, ensuring conversation state is properly saved and can be restored.
    """

    def __init__(
        self,
        conversation_id: Optional[int] = None,
        stateless: bool = False,
        ephemeral: bool = False,
        max_history_tokens: Optional[int] = None,
    ):
        """Initialize the database checkpoint saver.

        Args:
            conversation_id: Optional conversation ID to use.
            stateless: If True, disable checkpoint persistence.
            ephemeral: If True, disable conversation history persistence.
            max_history_tokens: When set, trim history to this token budget
                before returning a checkpoint.
        """
        super().__init__()
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self.conversation_id = conversation_id
        self.ephemeral = ephemeral
        self.message_history = DatabaseChatMessageHistory(
            conversation_id, ephemeral=ephemeral
        )
        self.stateless = stateless
        self.max_history_tokens = max_history_tokens
        # Instance-level LRU cache — keyed by thread_id (str(conversation_id)).
        # OrderedDict gives O(1) move-to-end for LRU ordering.
        self._checkpoint_state: OrderedDict[str, Any] = OrderedDict()

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
        del new_versions
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

            self.logger.debug(
                "DatabaseCheckpointSaver.put() called for conversation %s", self.conversation_id
            )

            # Extract messages from checkpoint
            if "messages" in checkpoint.get("channel_values", {}):
                messages = checkpoint["channel_values"]["messages"]

                self.logger.debug("Checkpoint has %d messages", len(messages))
                if messages:
                    last_msg = messages[-1]
                    last_msg_type = type(last_msg).__name__
                    last_msg_content = getattr(last_msg, "content", "")[:100]
                    self.logger.debug(
                        "Checkpoint persistence preview - type=%s, content=%r",
                        last_msg_type,
                        last_msg_content,
                    )

                # CRITICAL FIX: Only append NEW messages, don't clear existing ones.
                # The database stores rich message format (blocks, metadata, etc.)
                # that gets lost when we clear and re-save LangChain messages.
                #
                # Strategy: Count existing LangChain-compatible messages (user/assistant)
                # and only add messages beyond that count.

                # Refresh conversation from database to ensure we have latest state
                self.message_history._load_conversation()
                if not self.message_history.conversation_id:
                    # If we still don't have a conversation_id, DB persistence isn't available.
                    # Fall back to stateless semantics for this put() call.
                    self.logger.warning(
                        "⚠️ No conversation_id available; skipping DB message persistence for this checkpoint"
                    )
                    checkpoint_id = checkpoint.get("id") or str(uuid.uuid4())
                    return {
                        "configurable": {
                            "thread_id": str(uuid.uuid4()),
                            "checkpoint_id": checkpoint_id,
                        }
                    }
                raw_conv = self.message_history._conversation
                existing_value = (
                    raw_conv.value if raw_conv and raw_conv.value else []
                )

                # Count only user/assistant messages (what LangGraph sees)
                existing_langchain_count = sum(
                    1
                    for msg in existing_value
                    if msg.get("role") in ("user", "assistant", "bot")
                    and msg.get("metadata_type")
                    not in ("tool_calls", "tool_result")
                )
                checkpoint_count = len(messages)

                self.logger.debug(
                    "Comparing: DB has %d user/assistant msgs, checkpoint has %d messages",
                    existing_langchain_count, checkpoint_count,
                )

                # Only add messages that are NEW (beyond what's already in DB)
                if checkpoint_count > existing_langchain_count:
                    new_messages = messages[existing_langchain_count:]
                    self.logger.debug(
                        "Adding %d new messages to conversation", len(new_messages)
                    )
                    for msg in new_messages:
                        self.message_history.add_message(msg)
                    self.logger.debug(
                        "Appended %d new messages to conversation %s",
                        len(new_messages), self.message_history.conversation_id,
                    )
                elif checkpoint_count == existing_langchain_count:
                    self.logger.debug(
                        "No new messages to save (checkpoint matches DB count)"
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
                    self._checkpoint_state.move_to_end(thread_id)
                    if len(self._checkpoint_state) > _CHECKPOINT_STATE_MAX_SIZE:
                        self._checkpoint_state.popitem(last=False)
                    self.logger.debug(
                        "Stored full checkpoint state with %d messages for thread %s",
                        len(messages), thread_id,
                    )
                else:
                    self.logger.warning(
                        "Skipping checkpoint save - no changes detected (%d messages)", len(messages)
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
            self.logger.error("Error saving checkpoint: %s", e, exc_info=True)
            return config

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Fetch a checkpoint tuple using the given configuration.

        Args:
            config: Configuration specifying which checkpoint to retrieve.

        Returns:
            The requested checkpoint tuple, or None if not found.
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

            if thread_id and thread_id in self._checkpoint_state:
                state = self._checkpoint_state[thread_id]
                trimmed = self._trim_messages(state["messages"])
                checkpoint_data = state["checkpoint"]
                if trimmed is not state["messages"]:
                    checkpoint_data = dict(checkpoint_data)
                    checkpoint_data["channel_values"] = dict(
                        checkpoint_data.get("channel_values", {})
                    )
                    checkpoint_data["channel_values"]["messages"] = trimmed
                return CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint_data,
                    metadata=state["metadata"],
                    parent_config=None,
                )

            # Fallback: Load from database (may not have ToolMessages)
            messages = self.message_history.messages

            if not messages:
                return None

            messages = self._trim_messages(messages)

            checkpoint: Checkpoint = {
                "v": 1,
                "id": str(uuid.uuid4()),
                "ts": "",
                "channel_values": {
                    "messages": messages,
                },
                "channel_versions": {},
                "versions_seen": {},
                "updated_channels": None,
            }

            metadata: CheckpointMetadata = {
                "source": "update",
                "step": len(messages),
                "parents": {},
            }

            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=None,
            )

        except Exception as e:
            self.logger.error(
                "Error retrieving checkpoint: %s", e, exc_info=True
            )
            return None

    def _trim_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim message history to fit within max_history_tokens budget.

        Removes oldest messages (excluding the last user/assistant pair) when
        the token count exceeds the configured limit.  Returns the original
        list unchanged when no limit is set or it is not exceeded.
        """
        if not self.max_history_tokens or not messages:
            return messages

        total_tokens = count_tokens_approximately(messages)
        if total_tokens <= self.max_history_tokens:
            return messages

        # Keep trimming from the front (oldest) until we fit, but always
        # preserve at least the last 2 messages (most recent exchange).
        trimmed = list(messages)
        while len(trimmed) > 2 and count_tokens_approximately(trimmed) > self.max_history_tokens:
            trimmed.pop(0)

        self.logger.info(
            "History trimmed from %d to %d messages to fit %d token budget (%d tokens)",
            len(messages), len(trimmed), self.max_history_tokens,
            count_tokens_approximately(trimmed),
        )
        return trimmed

    def get(self, config: RunnableConfig) -> Optional[Checkpoint]:
        """Retrieve a checkpoint payload from the database.

        Args:
            config: Runtime configuration

        Returns:
            Checkpoint data or None if not found
        """
        checkpoint_tuple = self.get_tuple(config)
        if checkpoint_tuple is None:
            return None
        return checkpoint_tuple.checkpoint

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Store intermediate writes from graph execution.

        Args:
            config: Runtime configuration
            writes: Sequence of (channel, value) writes to store
            task_id: Unique identifier for the task
        """
        del task_path
        # TODO: persist intermediate writes so tool side-effects (write_file,
        # record_knowledge, generate_image, etc.) are not re-executed if the
        # server crashes between the tool call and the final LLM response.
        # For now, stash them in memory so they survive within a single process
        # lifetime, but they will be lost on server restart.
        thread_id = config.get("configurable", {}).get("thread_id") if config else None
        if thread_id and writes:
            state = self._checkpoint_state.get(thread_id)
            if state is not None:
                pending = state.setdefault("pending_writes", {})
                pending[task_id] = list(writes)
                self.logger.debug(
                    "put_writes: stored %d writes for task %s thread %s",
                    len(writes), task_id, thread_id,
                )
            else:
                self.logger.warning(
                    "put_writes: no checkpoint state for thread %s — intermediate "
                    "writes not persisted; tool results may re-execute on restart",
                    thread_id,
                )

    def list(
        self,
        config: Optional[RunnableConfig],
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
        del before

        if config is None:
            return
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
        if thread_id and thread_id in self._checkpoint_state:
            del self._checkpoint_state[thread_id]
            self.logger.info(
                "Cleared checkpoint state for thread %s", thread_id
            )
        else:
            self.logger.debug(
                "No checkpoint state to clear for thread %s", thread_id
            )

        if clear_history:
            self.message_history.clear()
            self.logger.info(
                "Cleared message history for conversation %s", self.conversation_id
            )

    def clear_thread(self, thread_id: str) -> None:
        """Clear checkpoint state for a specific thread.

        Args:
            thread_id: The thread ID to clear
        """
        if thread_id in self._checkpoint_state:
            del self._checkpoint_state[thread_id]
            self.logger.info(
                "Cleared checkpoint state for thread %s", thread_id
            )
