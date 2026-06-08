"""Test helpers for conversation summarization tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage


def _make_mock_chat_model(summary_text: str = "This is a test summary."):
    """Return a mock chat model that returns a fixed summary."""
    from langchain_core.messages import AIMessage as LC_AIMessage

    mock = MagicMock()
    mock.invoke.return_value = LC_AIMessage(content=summary_text)
    return mock


_DEFAULT_MSGS = [
    HumanMessage(content="hi"),
    AIMessage(content="hello"),
    HumanMessage(content="how are you?"),
    AIMessage(content="good"),
    HumanMessage(content="tell me a story"),
    AIMessage(content="once upon a time..."),
]


def _build_checkpoint(messages: list, thread_id: str) -> dict:
    """Return a checkpoint dict and in-memory state for one thread."""
    cp = {
        "v": 1,
        "id": "ckpt-1",
        "ts": "",
        "channel_values": {"messages": list(messages)},
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": None,
    }
    state = {"messages": list(messages), "checkpoint": cp, "metadata": {}}
    return {thread_id: state}


def _make_mock_owner(
    *,
    perform_conversation_summary: bool = True,
    summarize_after_n_turns: int = 4,
    chat_model=None,
    thread_id: str = "test-thread",
    messages: list | None = None,
):
    """Build a mock owner with summarization-ready state."""
    messages = messages or _DEFAULT_MSGS
    owner = MagicMock()
    owner.llm_generator_settings = None
    owner.llm_settings = MagicMock(
        perform_conversation_summary=perform_conversation_summary,
        summarize_after_n_turns=summarize_after_n_turns,
    )
    checkpoint_state = _build_checkpoint(messages, thread_id)
    memory = MagicMock()
    memory._checkpoint_state = checkpoint_state
    wm = MagicMock(_memory=memory, _thread_id=thread_id)
    if chat_model is not None:
        wm._original_chat_model = chat_model
    owner._workflow_manager = wm
    return owner, checkpoint_state


# ---------------------------------------------------------------------------
# Test: summarization not triggered when disabled
# ---------------------------------------------------------------------------
