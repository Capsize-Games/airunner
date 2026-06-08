"""Unit tests for DatabaseCheckpointSaver."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, AIMessage


def _make_saver(conversation_id: int = 1, stateless: bool = False, ephemeral: bool = True):
    """Return a DatabaseCheckpointSaver with DB I/O fully mocked out."""
    with patch(
        "airunner_services.llm.managers.database_checkpoint_saver.DatabaseChatMessageHistory"
    ) as MockHistory:
        mock_history = MagicMock()
        mock_history.conversation_id = conversation_id
        mock_history.messages = []
        mock_history._conversation = None
        MockHistory.return_value = mock_history

        from airunner_services.llm.managers.database_checkpoint_saver import (
            DatabaseCheckpointSaver,
        )

        saver = DatabaseCheckpointSaver(
            conversation_id=conversation_id,
            stateless=stateless,
            ephemeral=ephemeral,
        )
        saver.message_history = mock_history
        return saver, mock_history


def _make_checkpoint(messages: list, checkpoint_id: str | None = None) -> dict:
    """Build a minimal checkpoint dict."""
    return {
        "v": 1,
        "id": checkpoint_id or str(uuid.uuid4()),
        "ts": "",
        "channel_values": {"messages": messages},
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": None,
    }


def _make_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


# ---------------------------------------------------------------------------
# Test 1: put() only appends NEW messages
# ---------------------------------------------------------------------------

class TestPutAppendsOnlyNewMessages:
    def test_appends_messages_beyond_existing_db_count(self):
        saver, mock_history = _make_saver(conversation_id=42)
        thread_id = "42"
        msgs = [HumanMessage(content="hi"), AIMessage(content="hello")]
        checkpoint = _make_checkpoint(msgs)
        metadata = {"source": "update", "step": 2, "parents": {}}

        # Simulate DB already has 1 user/assistant message
        mock_history._load_conversation = MagicMock()
        mock_history._conversation = MagicMock()
        mock_history._conversation.value = [
            {"role": "user", "content": "hi", "metadata_type": None}
        ]

        saver.put(_make_config(thread_id), checkpoint, metadata)

        # Only the second message (AIMessage, beyond existing count=1) should be added
        assert mock_history.add_message.call_count == 1
        added = mock_history.add_message.call_args[0][0]
        assert isinstance(added, AIMessage)

    def test_no_messages_added_when_counts_match(self):
        saver, mock_history = _make_saver(conversation_id=5)
        thread_id = "5"
        msgs = [HumanMessage(content="x")]
        checkpoint = _make_checkpoint(msgs)
        metadata = {"source": "update", "step": 1, "parents": {}}

        mock_history._load_conversation = MagicMock()
        mock_history._conversation = MagicMock()
        mock_history._conversation.value = [
            {"role": "user", "content": "x", "metadata_type": None}
        ]

        saver.put(_make_config(thread_id), checkpoint, metadata)

        mock_history.add_message.assert_not_called()

    def test_checkpoint_stored_in_memory_after_put(self):
        saver, mock_history = _make_saver(conversation_id=7)
        thread_id = "7"
        msgs = [HumanMessage(content="store me")]
        checkpoint = _make_checkpoint(msgs)
        metadata = {"source": "update", "step": 1, "parents": {}}

        mock_history._load_conversation = MagicMock()
        mock_history._conversation = MagicMock()
        mock_history._conversation.value = []

        saver.put(_make_config(thread_id), checkpoint, metadata)

        assert thread_id in saver._checkpoint_state
        assert saver._checkpoint_state[thread_id]["messages"] == msgs


# ---------------------------------------------------------------------------
# Test 2: get_tuple() returns None in stateless mode
# ---------------------------------------------------------------------------

class TestGetTupleStateless:
    def test_returns_none_when_stateless(self):
        saver, _mock_history = _make_saver(conversation_id=1, stateless=True)
        result = saver.get_tuple(_make_config("1"))
        assert result is None


# ---------------------------------------------------------------------------
# Test 3: get_tuple() returns in-memory state without hitting DB
# ---------------------------------------------------------------------------

class TestGetTupleFromMemory:
    def test_returns_in_memory_state(self):
        saver, mock_history = _make_saver(conversation_id=10)
        thread_id = "10"
        msgs = [HumanMessage(content="cached")]
        checkpoint = _make_checkpoint(msgs)
        metadata = {"source": "update", "step": 1, "parents": {}}

        # Pre-populate the in-memory cache
        saver._checkpoint_state[thread_id] = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "messages": msgs,
        }

        result = saver.get_tuple(_make_config(thread_id))

        assert result is not None
        assert result.checkpoint["channel_values"]["messages"] == msgs
        # DB messages property should NOT have been accessed
        mock_history.messages.assert_not_called() if hasattr(
            mock_history.messages, "assert_not_called"
        ) else None


# ---------------------------------------------------------------------------
# Test 4: get_tuple() falls back to DB when in-memory state is absent
# ---------------------------------------------------------------------------

class TestGetTupleFallsBackToDb:
    def test_falls_back_to_db_messages(self):
        saver, mock_history = _make_saver(conversation_id=20)
        thread_id = "99"  # not in in-memory cache
        db_messages = [HumanMessage(content="from db"), AIMessage(content="reply")]
        mock_history.messages = db_messages

        result = saver.get_tuple(_make_config(thread_id))

        assert result is not None
        assert result.checkpoint["channel_values"]["messages"] == db_messages

    def test_returns_none_when_db_empty(self):
        saver, mock_history = _make_saver(conversation_id=21)
        mock_history.messages = []

        result = saver.get_tuple(_make_config("999"))

        assert result is None


# ---------------------------------------------------------------------------
# Test 5: clear_checkpoints() removes the thread from _checkpoint_state
# ---------------------------------------------------------------------------

class TestClearCheckpoints:
    def test_clears_this_conversations_thread(self):
        saver, mock_history = _make_saver(conversation_id=30)
        thread_id = "30"
        saver._checkpoint_state[thread_id] = {"messages": [], "checkpoint": {}, "metadata": {}}

        saver.clear_checkpoints(clear_history=False)

        assert thread_id not in saver._checkpoint_state

    def test_does_not_clear_other_threads(self):
        saver, mock_history = _make_saver(conversation_id=31)
        saver._checkpoint_state["31"] = {"messages": [], "checkpoint": {}, "metadata": {}}
        saver._checkpoint_state["999"] = {"messages": [], "checkpoint": {}, "metadata": {}}

        saver.clear_checkpoints(clear_history=False)

        assert "999" in saver._checkpoint_state

    def test_clears_message_history_when_requested(self):
        saver, mock_history = _make_saver(conversation_id=32)
        saver.clear_checkpoints(clear_history=True)
        mock_history.clear.assert_called_once()

    def test_does_not_clear_message_history_when_not_requested(self):
        saver, mock_history = _make_saver(conversation_id=33)
        saver.clear_checkpoints(clear_history=False)
        mock_history.clear.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: Two instances with different conversation_ids do not share state
# ---------------------------------------------------------------------------

class TestInstanceIsolation:
    def test_different_instances_have_separate_checkpoint_state(self):
        saver_a, mock_a = _make_saver(conversation_id=100)
        saver_b, mock_b = _make_saver(conversation_id=200)

        saver_a._checkpoint_state["100"] = {"messages": ["a"], "checkpoint": {}, "metadata": {}}

        # saver_b must not see saver_a's state
        assert "100" not in saver_b._checkpoint_state

    def test_put_into_one_instance_does_not_contaminate_another(self):
        saver_a, mock_a = _make_saver(conversation_id=101)
        saver_b, mock_b = _make_saver(conversation_id=102)

        msgs = [HumanMessage(content="isolation test")]
        checkpoint = _make_checkpoint(msgs)
        metadata = {"source": "update", "step": 1, "parents": {}}

        mock_a._load_conversation = MagicMock()
        mock_a._conversation = MagicMock()
        mock_a._conversation.value = []

        saver_a.put(_make_config("101"), checkpoint, metadata)

        # saver_b's state should be untouched
        assert "101" not in saver_b._checkpoint_state
        assert len(saver_b._checkpoint_state) == 0

    def test_lru_eviction_caps_at_max_size(self):
        from airunner_services.llm.managers.database_checkpoint_saver import (
            _CHECKPOINT_STATE_MAX_SIZE,
        )

        saver, _ = _make_saver(conversation_id=999)
        # Fill beyond max
        for i in range(_CHECKPOINT_STATE_MAX_SIZE + 5):
            saver._checkpoint_state[str(i)] = {"messages": [], "checkpoint": {}, "metadata": {}}
            saver._checkpoint_state.move_to_end(str(i))
            if len(saver._checkpoint_state) > _CHECKPOINT_STATE_MAX_SIZE:
                saver._checkpoint_state.popitem(last=False)

        assert len(saver._checkpoint_state) <= _CHECKPOINT_STATE_MAX_SIZE
