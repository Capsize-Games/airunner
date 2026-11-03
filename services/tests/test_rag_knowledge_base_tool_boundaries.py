"""Scoped catalog search and managed-save boundary regressions."""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from airunner_services.llm.tool_manager import ToolManager
from airunner_services.llm.workflow_manager import WorkflowState


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter_by(self, **kwargs):
        if kwargs.get("active"):
            return _Query([row for row in self.rows if row.active])
        return self

    def all(self):
        return list(self.rows)


class _Session:
    def __init__(self, rows):
        self.rows = rows

    def query(self, _model):
        return _Query(self.rows)


class _Manager:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.lock = threading.Lock()

    @contextmanager
    def session_scope(self):
        yield _Session(self.rows)


def _doc(path, active=True, indexed=False):
    return SimpleNamespace(path=path, active=active, indexed=indexed)


def _persistent_id(path):
    return hashlib.md5(os.path.normpath(os.path.abspath(path)).encode()).hexdigest()


def _search_wrapper(rows):
    from airunner_services.llm.core.tool_registry import ToolRegistry

    registry_tool = ToolRegistry.get("search_knowledge_base_documents")
    manager = _Manager(rows)
    import airunner_services.api.runtime as api_runtime

    api_runtime.get_api = lambda: manager
    tm = object.__new__(ToolManager)
    tm.rag_manager = manager
    tm._request_tool_defaults = {}
    tm._tool_action_handler = None
    tm.logger = logging.getLogger("rag-boundary-test")
    wrapped = tm._wrap_tool_with_dependencies(registry_tool)
    wrapped.name = registry_tool.name
    assert set(ToolNode([wrapped]).tools_by_name[registry_tool.name].get_input_schema().model_fields) == {
        "query",
        "k",
    }
    return wrapped


def _tool_graph(tool):
    import airunner_services.llm.managers.mixins.tool_execution_mixin as module

    module.WorkflowState = WorkflowState
    graph = StateGraph(WorkflowState)
    graph.add_node("tools", ToolNode([tool]))
    graph.set_entry_point("tools")
    graph.add_edge("tools", END)
    return graph.compile()


def _call(tool_name, args, call_id="call"):
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": tool_name, "args": args, "id": call_id, "type": "tool_call"}
                ],
            )
        ]
    }


def _parallel_calls(tool_name, calls):
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": tool_name, "args": args, "id": call_id, "type": "tool_call"}
                    for call_id, args in calls
                ],
            )
        ]
    }


def _save_wrapper(manager):
    from airunner_services.llm.core.tool_registry import ToolRegistry

    registry_tool = ToolRegistry.get("save_to_knowledge_base")
    tm = object.__new__(ToolManager)
    tm.rag_manager = manager
    tm._request_tool_defaults = {}
    tm._tool_action_handler = None
    tm.logger = logging.getLogger("rag-boundary-test")
    wrapped = tm._wrap_tool_with_dependencies(registry_tool)
    wrapped.name = registry_tool.name
    return wrapped


def test_search_toolnode_scope_excludes_out_of_scope_catalog_rows(monkeypatch):
    from airunner_services.llm.tools import rag_tools

    allowed = _doc("/managed/allowed/research-notes.md")
    private = _doc("/managed/private/research-notes.md")
    monkeypatch.setattr(rag_tools, "session_scope", _Manager([allowed, private]).session_scope)
    wrapped = _search_wrapper([allowed, private])
    graph = _tool_graph(wrapped)
    result = graph.invoke(
        _call("search_knowledge_base_documents", {"query": "research"}),
        config={"configurable": {"rag_document_scope": (_persistent_id(allowed.path),)}},
    )
    text = result["messages"][-1].content
    assert "allowed/research-notes.md" in text
    assert "private/research-notes.md" not in text


def test_search_toolnode_explicit_empty_scope_stays_empty(monkeypatch):
    from airunner_services.llm.tools import rag_tools

    rows = [_doc("/managed/research.md")]
    @contextmanager
    def unexpected_query():
        raise AssertionError("empty scope must return before database query")
        yield

    monkeypatch.setattr(rag_tools, "session_scope", unexpected_query)
    result = _tool_graph(_search_wrapper(rows)).invoke(
        _call("search_knowledge_base_documents", {"query": "research"}),
        config={"configurable": {"rag_document_scope": ()}},
    )
    assert "research.md" not in result["messages"][-1].content


def test_parallel_search_toolnodes_keep_scopes_isolated(monkeypatch):
    from airunner_services.llm.tools import rag_tools

    rows = [_doc("/managed/alpha/research.md"), _doc("/managed/beta/research.md")]
    monkeypatch.setattr(rag_tools, "session_scope", _Manager(rows).session_scope)
    graph = _tool_graph(_search_wrapper(rows))

    def invoke(path, call_id):
        return graph.invoke(
            _call("search_knowledge_base_documents", {"query": "research"}, call_id),
            config={"configurable": {"rag_document_scope": (_persistent_id(path),)}},
        )["messages"][-1].content

    with ThreadPoolExecutor(max_workers=2) as pool:
        alpha = pool.submit(invoke, rows[0].path, "alpha").result(timeout=10)
        beta = pool.submit(invoke, rows[1].path, "beta").result(timeout=10)
    assert "alpha/research.md" in alpha and "beta/research.md" not in alpha
    assert "beta/research.md" in beta and "alpha/research.md" not in beta


def test_search_does_not_discover_or_index(monkeypatch):
    from airunner_services.llm.tools import rag_tools

    row = _doc("/managed/not-indexed-research.md", indexed=False)
    manager = _Manager([row])
    monkeypatch.setattr(rag_tools, "session_scope", manager.session_scope)
    wrapper = _search_wrapper([row])
    import airunner_services.api.runtime as api_runtime

    class UnexpectedRagWork:
        def ensure_indexed_files(self, _paths):
            raise AssertionError("catalog search attempted indexing")

    api_runtime.get_api = lambda: SimpleNamespace(rag_manager=UnexpectedRagWork())
    graph = _tool_graph(wrapper)
    result = graph.invoke(
        _call("search_knowledge_base_documents", {"query": "research"}),
        config={"configurable": {"rag_document_scope": ()}},
    )["messages"][-1].content
    assert "not-indexed-research.md" not in result
    assert not hasattr(manager, "ensure_indexed_files")


def test_managed_save_rejects_escape_symlinks_and_overwrite(tmp_path, monkeypatch):
    from airunner_services.llm.tools import rag_tools

    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(rag_tools.PathSettings, "objects", SimpleNamespace(first=lambda: SimpleNamespace(base_path=str(base))), raising=False)
    created = []

    class Objects:
        def create(self, **kwargs):
            created.append(kwargs)
            return kwargs

    monkeypatch.setattr(rag_tools.Document, "objects", Objects(), raising=False)
    assert "Error" in rag_tools.save_to_knowledge_base("x", "safe", "../escape")
    assert not (tmp_path / "escape").exists()
    with pytest.raises(ValueError, match="dot components"):
        rag_tools._write_managed_knowledge_file(
            str(tmp_path / "base" / ".." / "outside"),
            "general",
            "x.txt",
            "x",
            "x",
        )

    symlink_target = tmp_path / "outside"
    symlink_target.mkdir()
    (base / "knowledge_base").symlink_to(symlink_target, target_is_directory=True)
    result = rag_tools.save_to_knowledge_base("x", "safe", "general")
    assert "Error saving" in result
    assert list(symlink_target.iterdir()) == []
    (base / "knowledge_base").unlink()

    saved = rag_tools.save_to_knowledge_base("original", "safe", "general")
    target = base / "knowledge_base" / "general" / "safe.txt"
    assert "saved and registered" in saved
    before = target.read_bytes()
    duplicate = rag_tools.save_to_knowledge_base("replacement", "safe", "general")
    assert "already exists" in duplicate
    assert target.read_bytes() == before
    assert len(created) == 1


def test_managed_save_enforces_bounds_and_concurrent_no_overwrite(tmp_path, monkeypatch):
    from airunner_services.llm.tools import rag_tools

    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(rag_tools.PathSettings, "objects", SimpleNamespace(first=lambda: SimpleNamespace(base_path=str(base))), raising=False)
    registrations = []
    lock = threading.Lock()

    class Objects:
        def create(self, **kwargs):
            with lock:
                registrations.append(kwargs)
            return kwargs

    monkeypatch.setattr(rag_tools.Document, "objects", Objects(), raising=False)
    assert "65536" in rag_tools.save_to_knowledge_base("x" * 65537, "large")
    assert "empty" in rag_tools.save_to_knowledge_base("  ", "empty")

    tool = _save_wrapper(_Manager([]))
    graph = _tool_graph(tool)
    result = graph.invoke(
        _parallel_calls(
            "save_to_knowledge_base",
            [("save-one", {"content": "one", "title": "race", "category": "general"}),
             ("save-two", {"content": "two", "title": "race", "category": "general"})],
        )
    )
    texts = [message.content for message in result["messages"][-2:]]
    assert sum("saved and registered" in text for text in texts) == 1
    assert sum("already exists" in text for text in texts) == 1
    assert len(registrations) == 1


def test_scoped_save_is_in_next_request_scope_after_workflow_restart(tmp_path, monkeypatch):
    from airunner_services.database.models import target_files as target_files_module
    from airunner_services.llm.managers.mixins.request_handling_mixin import (
        RequestHandlingMixin,
    )
    from airunner_services.llm.managers.mixins.generation_workflow_support import (
        sync_request_scope_to_workflow_manager,
    )
    from airunner_services.llm.managers.mixins.streaming_mixin import StreamingMixin
    from airunner_services.llm.tools import rag_tools

    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(
        rag_tools.PathSettings,
        "objects",
        SimpleNamespace(first=lambda: SimpleNamespace(base_path=str(base))),
        raising=False,
    )
    documents = []
    targets = []

    class DocumentObjects:
        def create(self, **kwargs):
            row = SimpleNamespace(**kwargs)
            documents.append(row)
            return row

    class TargetObjects:
        def create(self, **kwargs):
            row = SimpleNamespace(**kwargs)
            targets.append(row)
            return row

    monkeypatch.setattr(rag_tools.Document, "objects", DocumentObjects(), raising=False)
    monkeypatch.setattr(rag_tools.TargetFiles, "objects", TargetObjects(), raising=False)

    workflow = object.__new__(StreamingMixin)
    workflow._thread_id = "test-thread"
    workflow.chatbot = SimpleNamespace(id=71)
    config = workflow._create_config()
    assert config["configurable"]["chatbot_id"] == 71
    save_tool = _save_wrapper(_Manager([]))
    save_node = ToolNode([save_tool])
    assert set(save_node.tools_by_name["save_to_knowledge_base"].get_input_schema().model_fields) == {
        "content",
        "title",
        "category",
    }

    result = _tool_graph(save_tool).invoke(
        _call(
            "save_to_knowledge_base",
            {"content": "remember this", "title": "scoped-note", "category": "general"},
        ),
        config=config,
    )["messages"][-1].content
    assert "saved and registered" in result
    assert len(documents) == len(targets) == 1
    assert targets[0].chatbot_id == 71
    assert targets[0].file_path == documents[0].path

    class ScopeQuery:
        def __init__(self, model, rows):
            self.model = model
            self.rows = rows
            self.criteria = {}
            self.paths = None

        def filter_by(self, **criteria):
            self.criteria = criteria
            return self

        def filter(self, expression):
            self.paths = set(expression.right.value)
            return self

        def all(self):
            rows = self.rows
            if self.criteria:
                rows = [
                    row
                    for row in rows
                    if all(getattr(row, key) == value for key, value in self.criteria.items())
                ]
            if self.paths is not None:
                rows = [row for row in rows if row.path in self.paths]
            return rows

    class ScopeSession:
        def query(self, model):
            return ScopeQuery(model, targets if model is target_files_module.TargetFiles else documents)

    @contextmanager
    def scope_session():
        yield ScopeSession()

    monkeypatch.setattr("airunner_services.database.session.session_scope", scope_session)

    class Owner(RequestHandlingMixin):
        def __init__(self, chatbot_id):
            self.chatbot = SimpleNamespace(id=chatbot_id)

    next_scope = RequestHandlingMixin._request_rag_document_scope(
        Owner(71), SimpleNamespace(rag_files=None)
    )
    other_scope = RequestHandlingMixin._request_rag_document_scope(
        Owner(72), SimpleNamespace(rag_files=None)
    )
    assert next_scope == (_persistent_id(documents[0].path),)
    assert other_scope == ()

    owner = SimpleNamespace(
        _workflow_manager=workflow,
        _current_request_id="switch-request",
        llm_request=None,
        _request_chatbot=SimpleNamespace(id=72),
        chatbot=SimpleNamespace(id=72),
    )
    sync_request_scope_to_workflow_manager(owner)
    switched_config = workflow._create_config()
    assert switched_config["configurable"]["chatbot_id"] == 72
    assert set(save_node.tools_by_name["save_to_knowledge_base"].get_input_schema().model_fields) == {
        "content",
        "title",
        "category",
    }


def test_save_reports_registration_and_notification_partial_failures(tmp_path, monkeypatch):
    from airunner_services.llm.tools import rag_tools

    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(
        rag_tools.PathSettings,
        "objects",
        SimpleNamespace(first=lambda: SimpleNamespace(base_path=str(base))),
        raising=False,
    )
    monkeypatch.setattr(
        rag_tools.Document,
        "objects",
        SimpleNamespace(create=lambda **_kwargs: None),
        raising=False,
    )
    failed_registration = rag_tools.save_to_knowledge_base("x", "registry-failure")
    assert "written" in failed_registration and "registration failed" in failed_registration
    persisted = base / "knowledge_base" / "general" / "registry-failure.txt"
    assert persisted.exists()

    monkeypatch.setattr(
        rag_tools.Document,
        "objects",
        SimpleNamespace(create=lambda **kwargs: kwargs),
        raising=False,
    )
    monkeypatch.setattr(
        rag_tools.TargetFiles,
        "objects",
        SimpleNamespace(create=lambda **kwargs: kwargs),
        raising=False,
    )

    class BrokenSignal:
        def emit_signal(self, *_args, **_kwargs):
            raise RuntimeError("synthetic notification failure")

    failure = rag_tools.save_to_knowledge_base(
        "x",
        "notification-failure",
        api=BrokenSignal(),
        config={"configurable": {"chatbot_id": 71}},
    )
    assert "saved and registered" in failure and "notification failed" in failure


def test_scoped_save_without_chatbot_identity_is_rejected_before_write(tmp_path, monkeypatch):
    from airunner_services.llm.tools import rag_tools

    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(
        rag_tools.PathSettings,
        "objects",
        SimpleNamespace(first=lambda: SimpleNamespace(base_path=str(base))),
        raising=False,
    )
    response = rag_tools.save_to_knowledge_base(
        "x",
        "scoped-without-owner",
        config={"configurable": {"rag_document_scope": ("some-doc-id",)}},
    )
    assert "no chatbot ownership identity" in response
    assert not (base / "knowledge_base").exists()


@pytest.mark.parametrize("failed_sync", [1, 2])
def test_save_fsync_failures_do_not_register_unconfirmed_file(
    tmp_path, monkeypatch, failed_sync
):
    from airunner_services.llm.tools import rag_tools

    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(
        rag_tools.PathSettings,
        "objects",
        SimpleNamespace(first=lambda: SimpleNamespace(base_path=str(base))),
        raising=False,
    )
    registrations = []

    class DocumentObjects:
        def create(self, **kwargs):
            registrations.append(kwargs)
            return kwargs

    monkeypatch.setattr(rag_tools.Document, "objects", DocumentObjects(), raising=False)
    original_fsync = os.fsync
    count = 0

    def fail_once(fd):
        nonlocal count
        count += 1
        if count == failed_sync:
            raise OSError("synthetic fsync failure")
        return original_fsync(fd)

    monkeypatch.setattr(rag_tools.os, "fsync", fail_once)
    response = rag_tools.save_to_knowledge_base("payload", f"sync-{failed_sync}")
    expected = base / "knowledge_base" / "general" / f"sync-{failed_sync}.txt"
    failed_stage = "file fsync" if failed_sync == 1 else "directory fsync"
    assert failed_stage in response and "removed" in response
    assert not expected.exists()
    assert registrations == []


def test_partial_write_cleanup_removes_only_created_entry(tmp_path, monkeypatch):
    from airunner_services.llm.tools import rag_tools

    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(
        rag_tools.PathSettings,
        "objects",
        SimpleNamespace(first=lambda: SimpleNamespace(base_path=str(base))),
        raising=False,
    )
    registrations = []
    monkeypatch.setattr(
        rag_tools.Document,
        "objects",
        SimpleNamespace(create=lambda **kwargs: registrations.append(kwargs)),
        raising=False,
    )
    real_write = os.write
    writes = 0

    def partial_then_fail(fd, data):
        nonlocal writes
        writes += 1
        if writes == 1:
            return real_write(fd, data[:4])
        raise OSError("synthetic partial write failure")

    monkeypatch.setattr(rag_tools.os, "write", partial_then_fail)
    response = rag_tools.save_to_knowledge_base("payload-long-enough", "partial")
    path = base / "knowledge_base" / "general" / "partial.txt"
    assert "write failed" in response and "removed" in response
    assert not path.exists()
    assert registrations == []
