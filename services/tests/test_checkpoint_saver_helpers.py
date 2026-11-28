"""Unit tests for the checkpoint-saver extraction helpers.

_cached_checkpoint and _build_db_checkpoint were extracted to keep
get_tuple within the long-function threshold. These tests pin the
memory-hit path, the miss path, and the DB checkpoint shape.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.llm.managers.database_checkpoint_saver import (
    DatabaseCheckpointSaver,
)


def _make_saver(state=None, messages=None):
    saver = DatabaseCheckpointSaver.__new__(DatabaseCheckpointSaver)
    saver.stateless = False
    saver.conversation_id = "conv-1"
    saver.logger = MagicMock()
    saver._checkpoint_state = state or {}
    saver.message_history = SimpleNamespace(messages=messages or [])
    return saver


def test_cached_hit_returns_tuple():
    saver = _make_saver(
        state={
            "t1": {
                "checkpoint": {"v": 1},
                "metadata": {"step": 2},
                "messages": ["m"],
            }
        }
    )
    result = saver._cached_checkpoint("t1", {"configurable": {}})
    assert result is not None
    assert result.checkpoint == {"v": 1}
    assert result.metadata == {"step": 2}
    assert result.parent_config is None


def test_cached_miss_returns_none():
    saver = _make_saver()
    assert saver._cached_checkpoint("nope", {}) is None


def test_cached_falsy_thread_id_misses():
    saver = _make_saver(state={"": {"checkpoint": 1, "metadata": {}, "messages": []}})
    assert saver._cached_checkpoint("", {}) is None


def test_db_checkpoint_shape():
    saver = _make_saver()
    result = saver._build_db_checkpoint({"configurable": {}}, ["a", "b"])
    assert result.checkpoint["v"] == 1
    assert result.checkpoint["channel_values"] == {"messages": ["a", "b"]}
    assert result.metadata == {"source": "update", "step": 2, "parents": {}}
    assert result.parent_config is None


def test_db_checkpoint_ids_are_unique():
    saver = _make_saver()
    first = saver._build_db_checkpoint({}, ["a"])
    second = saver._build_db_checkpoint({}, ["a"])
    assert first.checkpoint["id"] != second.checkpoint["id"]


def test_get_tuple_stateless_returns_none():
    saver = _make_saver()
    saver.stateless = True
    assert saver.get_tuple({}) is None


def test_get_tuple_uses_memory_hit():
    saver = _make_saver(
        state={
            "t1": {
                "checkpoint": {"v": 1},
                "metadata": {},
                "messages": ["m"],
            }
        }
    )
    result = saver.get_tuple({"configurable": {"thread_id": "t1"}})
    assert result is not None
    assert result.checkpoint == {"v": 1}


def test_get_tuple_no_messages_returns_none():
    saver = _make_saver(messages=[])
    assert saver.get_tuple({"configurable": {}}) is None
