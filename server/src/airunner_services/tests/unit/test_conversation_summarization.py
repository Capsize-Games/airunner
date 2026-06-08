"""Unit tests for in-context conversation summarization."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest_summarization import _make_mock_chat_model, _make_mock_owner
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestSummarizationDisabled:
    def test_skips_when_perform_conversation_summary_false(self):
        owner, checkpoint_state = _make_mock_owner(
            perform_conversation_summary=False,
        )
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)

        # Messages should be unchanged
        state = checkpoint_state["test-thread"]
        assert len(state["messages"]) == 6

    def test_skips_when_threshold_zero(self):
        owner, checkpoint_state = _make_mock_owner(
            summarize_after_n_turns=0,
        )
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)

        state = checkpoint_state["test-thread"]
        assert len(state["messages"]) == 6

    def test_skips_when_messages_not_exceed_threshold(self):
        owner, checkpoint_state = _make_mock_owner(
            summarize_after_n_turns=10,
        )
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)

        state = checkpoint_state["test-thread"]
        assert len(state["messages"]) == 6  # unchanged


# ---------------------------------------------------------------------------
# Test: summarization triggered and compresses correctly
# ---------------------------------------------------------------------------


class TestSummarizationCompression:
    def test_compresses_old_messages_into_summary(self):
        chat_model = _make_mock_chat_model("Compressed summary text.")
        owner, checkpoint_state = _make_mock_owner(
            summarize_after_n_turns=3,
            chat_model=chat_model,
        )
        # 6 messages, threshold=3 → summarize oldest 3
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)

        state = checkpoint_state["test-thread"]
        new_messages = state["messages"]

        # Should have 1 summary SystemMessage + 3 recent messages = 4 total
        assert len(new_messages) == 4
        assert isinstance(new_messages[0], SystemMessage)
        assert "Compressed summary text." in new_messages[0].content
        assert isinstance(new_messages[1], AIMessage)
        assert new_messages[1].content == "good"

    def test_checkpoint_channel_values_also_updated(self):
        chat_model = _make_mock_chat_model("Channel summary.")
        owner, checkpoint_state = _make_mock_owner(
            summarize_after_n_turns=2,
            chat_model=chat_model,
        )
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)

        state = checkpoint_state["test-thread"]
        channel_messages = state["checkpoint"]["channel_values"]["messages"]

        # Verify channel_values matches the state messages
        assert len(channel_messages) == len(state["messages"])
        assert channel_messages == state["messages"]

    def test_preserves_recent_messages_in_order(self):
        chat_model = _make_mock_chat_model("Ordered summary.")
        owner, checkpoint_state = _make_mock_owner(
            summarize_after_n_turns=4,
            chat_model=chat_model,
        )
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)

        state = checkpoint_state["test-thread"]
        new_messages = state["messages"]

        # Last 4 messages should be preserved in order:
        # HumanMessage("how are you?"), AIMessage("good"),
        # HumanMessage("tell me a story"), AIMessage("once upon a time...")
        assert new_messages[-4].content == "how are you?"
        assert new_messages[-3].content == "good"
        assert new_messages[-2].content == "tell me a story"
        assert new_messages[-1].content == "once upon a time..."


# ---------------------------------------------------------------------------
# Test: edge cases and robustness
# ---------------------------------------------------------------------------


class TestSummarizationEdgeCases:
    def test_skips_when_no_workflow_manager(self):
        owner = MagicMock()
        owner._workflow_manager = None
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        # Should not raise
        maybe_summarize_checkpoint(owner)

    def test_skips_when_no_memory(self):
        owner, _ = _make_mock_owner()
        owner._workflow_manager._memory = None
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)
        # Should not raise

    def test_skips_when_no_checkpoint_state_for_thread(self):
        owner, _ = _make_mock_owner(thread_id="missing-thread")
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)
        # Should not raise — thread "missing-thread" has no state

    def test_no_llm_call_when_empty_messages(self):
        owner, checkpoint_state = _make_mock_owner(
            summarize_after_n_turns=1,
            messages=[HumanMessage(content="only one")],
        )
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)
        # Only 1 message, threshold=1 → not exceeded, no compression
        state = checkpoint_state["test-thread"]
        assert len(state["messages"]) == 1

    def test_handles_llm_returning_none(self):
        chat_model = _make_mock_chat_model("")
        chat_model.invoke.return_value = MagicMock(content=None)
        owner, checkpoint_state = _make_mock_owner(
            summarize_after_n_turns=3,
            chat_model=chat_model,
        )
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        maybe_summarize_checkpoint(owner)
        # No compression should happen — LLM returned empty
        state = checkpoint_state["test-thread"]
        assert len(state["messages"]) == 6

    def test_handles_llm_exception_gracefully(self):
        chat_model = MagicMock()
        chat_model.invoke.side_effect = RuntimeError("LLM crash")
        owner, checkpoint_state = _make_mock_owner(
            summarize_after_n_turns=3,
            chat_model=chat_model,
        )
        from airunner_services.llm.managers.mixins.conversation_summarization import (
            maybe_summarize_checkpoint,
        )

        # Should not propagate
        maybe_summarize_checkpoint(owner)
        state = checkpoint_state["test-thread"]
        assert len(state["messages"]) == 6  # unchanged
