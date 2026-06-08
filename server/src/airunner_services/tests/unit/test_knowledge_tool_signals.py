"""Integration tests for knowledge tool signal emission and workflow state isolation.

Tests:
  1. record_knowledge emits KNOWLEDGE_FACT_ADDED
  2. recall_knowledge never emits KNOWLEDGE_FACT_ADDED (read-only)
  3. delete_knowledge emits KNOWLEDGE_FACT_DELETED (not KNOWLEDGE_FACT_ADDED)
  4. update_knowledge emits KNOWLEDGE_FACT_UPDATED (not KNOWLEDGE_FACT_ADDED)
  5. Concurrent tool invocations via ContextVar do not corrupt each other's state
  6. put_writes stashes intermediate writes in _checkpoint_state (in-memory survive
     within the process after a simulated mid-chain server crash)
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_api(captured_signals: list) -> MagicMock:
    api = MagicMock()
    api.emit_signal = lambda code, data: captured_signals.append((code, data))
    return api


def _mock_kb(add_ok=True, delete_ok=True, update_ok=True, facts=None):
    kb = MagicMock()
    kb.add_fact.return_value = add_ok
    kb.delete_fact.return_value = (delete_ok, 1)
    kb.update_fact.return_value = (update_ok, 1)
    kb.search_rag.return_value = facts or ["- fact 1", "- fact 2"]
    kb.search.return_value = facts or ["- fact 1"]
    kb.search_tfidf.return_value = facts or ["- fact 1"]
    return kb


# ---------------------------------------------------------------------------
# Test 1-4: Knowledge tool signal correctness
# ---------------------------------------------------------------------------

class TestKnowledgeToolSignals:
    def test_record_emits_fact_added(self):
        from airunner_services.contract_enums import SignalCode
        from airunner_services.llm.tools.knowledge_tools.record import (
            record_knowledge,
        )

        signals: list = []
        kb = _mock_kb()
        api = _mock_api(signals)

        with patch(
            "airunner_services.knowledge.get_knowledge_base",
            return_value=kb,
        ):
            result = record_knowledge(
                fact="User prefers dark mode",
                section="Preferences",
                api=api,
            )

        assert "✓" in result
        assert len(signals) == 1
        code, _data = signals[0]
        assert code == SignalCode.KNOWLEDGE_FACT_ADDED

    def test_delete_emits_fact_deleted_not_added(self):
        from airunner_services.contract_enums import SignalCode
        from airunner_services.llm.tools.knowledge_tools.delete import (
            delete_knowledge,
        )

        signals: list = []
        kb = _mock_kb()
        api = _mock_api(signals)

        with patch(
            "airunner_services.knowledge.get_knowledge_base",
            return_value=kb,
        ):
            result = delete_knowledge(text="User prefers dark mode", api=api)

        assert "✓" in result
        assert len(signals) == 1
        code, _data = signals[0]
        assert code == SignalCode.KNOWLEDGE_FACT_DELETED
        assert code != SignalCode.KNOWLEDGE_FACT_ADDED

    def test_update_emits_fact_updated_not_added(self):
        from airunner_services.contract_enums import SignalCode
        from airunner_services.llm.tools.knowledge_tools.update import (
            update_knowledge,
        )

        signals: list = []
        kb = _mock_kb()
        api = _mock_api(signals)

        with patch(
            "airunner_services.knowledge.get_knowledge_base",
            return_value=kb,
        ):
            result = update_knowledge(
                find_text="dark mode",
                replace_text="light mode",
                api=api,
            )

        assert "✓" in result
        assert len(signals) == 1
        code, _data = signals[0]
        assert code == SignalCode.KNOWLEDGE_FACT_UPDATED
        assert code != SignalCode.KNOWLEDGE_FACT_ADDED

    def test_recall_emits_no_signal(self):
        from airunner_services.llm.tools.knowledge_tools.recall import (
            recall_knowledge,
        )

        signals: list = []
        kb = _mock_kb()
        api = _mock_api(signals)

        with patch(
            "airunner_services.knowledge.get_knowledge_base",
            return_value=kb,
        ):
            result = recall_knowledge(query="dark mode preference", api=api)

        assert len(signals) == 0
        assert isinstance(result, str)

    def test_record_failure_emits_no_signal(self):
        from airunner_services.llm.tools.knowledge_tools.record import (
            record_knowledge,
        )

        signals: list = []
        kb = _mock_kb(add_ok=False)
        api = _mock_api(signals)

        with patch(
            "airunner_services.knowledge.get_knowledge_base",
            return_value=kb,
        ):
            record_knowledge(fact="test fact", api=api)

        assert len(signals) == 0


# ---------------------------------------------------------------------------
# Test 5: Concurrent ContextVar isolation — two async tasks do not see each
# other's workflow state.
# ---------------------------------------------------------------------------

class TestWorkflowStateContextVarIsolation:
    @pytest.mark.asyncio
    async def test_concurrent_tasks_have_independent_workflow_state(self):
        from airunner_services.llm.agents.workflow_tools import (
            _workflow_state_var,
            is_workflow_active,
        )
        from airunner_services.llm.agents.workflow_state import (
            WorkflowState as AgentWorkflowState,
            WorkflowType,
        )

        results: dict = {}

        async def task_coding():
            state = AgentWorkflowState(workflow_type=WorkflowType.CODING)
            token = _workflow_state_var.set(state)
            await asyncio.sleep(0)  # yield to other task
            results["coding_active"] = is_workflow_active()
            _workflow_state_var.reset(token)

        async def task_idle():
            # No workflow state set — should NOT see the coding task's state
            await asyncio.sleep(0)
            results["idle_active"] = is_workflow_active()

        await asyncio.gather(task_coding(), task_idle())

        assert results["coding_active"] is True
        assert results["idle_active"] is False


# ---------------------------------------------------------------------------
# Test 6: put_writes stores intermediate writes in _checkpoint_state
# ---------------------------------------------------------------------------

class TestPutWritesInMemoryPersistence:
    def _make_saver(self, conversation_id: int = 1):
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
                conversation_id=conversation_id, ephemeral=True
            )
            saver.message_history = mock_history
            return saver

    def test_put_writes_stores_in_checkpoint_state(self):
        saver = self._make_saver(conversation_id=50)
        thread_id = "50"
        # Pre-populate checkpoint state so put_writes has a state to attach to
        saver._checkpoint_state[thread_id] = {
            "checkpoint": {},
            "metadata": {},
            "messages": [HumanMessage(content="test")],
        }

        task_id = str(uuid.uuid4())
        writes = [("messages", HumanMessage(content="tool result"))]
        config = {"configurable": {"thread_id": thread_id}}

        saver.put_writes(config, writes, task_id)

        pending = saver._checkpoint_state[thread_id].get("pending_writes", {})
        assert task_id in pending
        assert pending[task_id] == list(writes)

    def test_put_writes_without_checkpoint_state_does_not_crash(self):
        saver = self._make_saver(conversation_id=51)
        # No pre-existing checkpoint state for thread 51
        config = {"configurable": {"thread_id": "51"}}
        writes = [("messages", "some value")]

        # Should not raise — just log a warning
        saver.put_writes(config, writes, "task-xyz")

    def test_put_writes_accumulate_across_multiple_tasks(self):
        saver = self._make_saver(conversation_id=52)
        thread_id = "52"
        saver._checkpoint_state[thread_id] = {
            "checkpoint": {},
            "metadata": {},
            "messages": [],
        }

        config = {"configurable": {"thread_id": thread_id}}
        task_a = "task-a"
        task_b = "task-b"

        saver.put_writes(config, [("tool_a_result", "val_a")], task_a)
        saver.put_writes(config, [("tool_b_result", "val_b")], task_b)

        pending = saver._checkpoint_state[thread_id]["pending_writes"]
        assert task_a in pending
        assert task_b in pending
