"""ToolManager keeps per-invocation RAG scope hidden and isolated in ToolNode."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from airunner_services.llm.tool_manager import ToolManager
from airunner_services.llm.managers.mixins.tool_execution_mixin import (
    ToolExecutionMixin,
)
from airunner_services.llm.workflow_manager import WorkflowState


class _RagManager:
    def __init__(self):
        self.calls: list[tuple[str, tuple[str, ...] | None]] = []
        self.lock = threading.Lock()

    def search(self, query, *, k, doc_ids):
        allowed = tuple(doc_ids) if doc_ids is not None else None
        with self.lock:
            self.calls.append((query, allowed))
        label = ",".join(allowed or ("unscoped",))
        return [
            Document(
                page_content=f"result for {label}",
                metadata={"source": label},
            )
        ]


def _wrapped_rag_search(manager: _RagManager):
    """Use ToolManager's production dependency wrapper without model setup."""
    tool_manager = object.__new__(ToolManager)
    tool_manager.rag_manager = manager
    tool_manager._request_tool_defaults = {}
    tool_manager._tool_action_handler = None
    tool_manager.logger = logging.getLogger("rag-tool-config-test")
    return tool_manager._get_tool_by_name("rag_search")


def _call(call_id: str, query: str):
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "rag_search",
                        "args": {"query": query},
                        "id": call_id,
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }


class _Policy:
    def prepare(self, state, tool_calls):
        return state, tool_calls, None

    def complete(self, _tool_calls):
        pass


class _WorkflowHarness(ToolExecutionMixin):
    def __init__(self, manager):
        self._tools = [_wrapped_rag_search(manager)]
        self._policy = _Policy()
        self.logger = logging.getLogger("rag-tool-config-test")

    def _get_forced_tool_policy(self):
        return self._policy

    def _emit_starting_status(self, _calls):
        pass

    def _sanitize_tool_functions(self):
        pass

    def _emit_completed_status(self, _state, _calls):
        pass


def _custom_tool_graph(manager: _RagManager):
    # WorkflowBuildingMixin installs this type into the function globals before
    # compiling its graph so LangGraph can resolve the state annotation.
    import airunner_services.llm.managers.mixins.tool_execution_mixin as module

    module.WorkflowState = WorkflowState
    harness = _WorkflowHarness(manager)
    graph = StateGraph(WorkflowState)
    graph.add_node("tools", harness._execute_tools_with_status)
    graph.set_entry_point("tools")
    graph.add_edge("tools", END)
    return graph.compile(), harness


def test_toolnode_injects_config_without_exposing_it_in_tool_schema():
    manager = _RagManager()
    wrapped = _wrapped_rag_search(manager)
    tool_node = ToolNode([wrapped])
    wrapped_tool = tool_node.tools_by_name["rag_search"]
    visible_fields = set(wrapped_tool.get_input_schema().model_fields)

    assert visible_fields == {"query"}
    assert "api" not in visible_fields
    assert "config" not in visible_fields

    graph, _harness = _custom_tool_graph(manager)
    result = graph.invoke(
        _call("scope-call", "scope query"),
        config={"configurable": {"rag_document_scope": ("allowed-doc",)}},
    )

    assert manager.calls == [("scope query", ("allowed-doc",))]
    tool_message = result["messages"][-1]
    assert "allowed-doc" in tool_message.content


def test_parallel_toolnode_invocations_keep_rag_scopes_isolated():
    manager = _RagManager()
    graph, _harness = _custom_tool_graph(manager)

    def invoke(query: str, doc_id: str):
        return graph.invoke(
            _call(f"call-{doc_id}", query),
            config={
                "configurable": {
                    "rag_document_scope": (doc_id,),
                }
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        alpha_future = executor.submit(invoke, "query alpha", "doc-alpha")
        beta_future = executor.submit(invoke, "query beta", "doc-beta")
        alpha = alpha_future.result(timeout=20)
        beta = beta_future.result(timeout=20)
    observed = dict(manager.calls)

    assert observed == {
        "query alpha": ("doc-alpha",),
        "query beta": ("doc-beta",),
    }
    alpha_text = alpha["messages"][-1].content
    beta_text = beta["messages"][-1].content
    assert "doc-alpha" in alpha_text and "doc-beta" not in alpha_text
    assert "doc-beta" in beta_text and "doc-alpha" not in beta_text
