"""Request-scoped markdown knowledge tools: scope, ingestion, storage.

The RAG catalog tools (``save_to_knowledge_base`` /
``search_knowledge_base_documents``) already enforce per-request document
scopes, explicit ingestion, and managed storage. These regressions extend
the same contract to the markdown memory tools in ``knowledge_tools.py``
backed by ``airunner_services.knowledge``:

- ``recall_knowledge`` honors the hidden per-request ``rag_document_scope``
  (an explicitly empty scope returns before any search, index, or database
  work) and never triggers implicit indexing/registration during a model
  tool call.
- ``record/update/delete_knowledge`` reject empty patterns before touching
  files and reject scoped writes that carry no chatbot ownership identity
  before writing.
- Date-addressed access stays inside the knowledge directory.
- Tool names and visible schemas are unchanged (``config`` stays hidden).

Evidence uses real ``ToolNode`` graphs, a real SQLite ORM (for scope
routing and proving no implicit ``Document`` registration), a real
numpy-backed retriever for the RAG path, and real markdown files for
persistence. No model runs.
"""

from __future__ import annotations

import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace

import numpy as np
import pytest
from langchain_core.documents import Document as LangDocument
from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode


@pytest.fixture()
def isolated_knowledge_base(tmp_path, monkeypatch):
    """Point the knowledge tools at an isolated markdown store."""
    from airunner_services import knowledge as knowledge_module
    from airunner_services.knowledge import KnowledgeBase

    store = tmp_path / "knowledge"
    store.mkdir()
    instance = KnowledgeBase(knowledge_dir=store)
    monkeypatch.setattr(
        knowledge_module, "get_knowledge_base", lambda: instance
    )
    return SimpleNamespace(store=store, module=knowledge_module, kb=instance)


@pytest.fixture()
def managed_sqlite_database(tmp_path, monkeypatch):
    """Real SQLite ORM, mirroring the RAG catalog integration test."""
    monkeypatch.setenv(
        "AIRUNNER_DATABASE_URL", f"sqlite:///{tmp_path / 'service.sqlite3'}"
    )
    monkeypatch.setenv("AIRUNNER_DB_TENANCY", "single")
    from airunner_services.database import models  # noqa: F401
    import airunner_services.database.base as base_module
    import airunner_services.database.session as db_session
    from airunner_services.database.base import Base, set_objects_factory
    from airunner_services.database.base_manager import RealBaseManager
    from airunner_services.database.models.chatbot import Chatbot
    from airunner_services.database.models.document import Document
    from airunner_services.database.models.path_settings import PathSettings
    from airunner_services.database.models.target_files import TargetFiles

    prior_factory = base_module._objects_factory
    missing = object()
    model_classes = (Chatbot, Document, PathSettings, TargetFiles)
    prior_objects = {
        model: model.__dict__.get("_objects", missing)
        for model in model_classes
    }
    set_objects_factory(RealBaseManager)
    for model in model_classes:
        model._objects = None

    db_session.reset_engine()
    try:
        Base.metadata.create_all(db_session._get_engine("default"))
        yield SimpleNamespace(
            session_module=db_session,
            chatbot_model=Chatbot,
            document_model=Document,
            target_files_model=TargetFiles,
        )
    finally:
        db_session.reset_engine()
        base_module._objects_factory = prior_factory
        for model, previous in prior_objects.items():
            if previous is missing:
                if "_objects" in model.__dict__:
                    delattr(model, "_objects")
            else:
                model._objects = previous


def _persistent_id(path):
    canonical = os.path.normpath(os.path.abspath(path))
    return hashlib.md5(canonical.encode()).hexdigest()


def _tool_node(tool_name, api_stub, monkeypatch):
    import airunner_services.api.runtime as api_runtime
    from airunner_services.llm.tool_manager import ToolManager
    from airunner_services.llm.core.tool_registry import ToolRegistry

    monkeypatch.setattr(api_runtime, "get_api", lambda: api_stub)
    tool_info = ToolRegistry.get(tool_name)
    manager = object.__new__(ToolManager)
    manager.rag_manager = SimpleNamespace()
    manager._request_tool_defaults = {}
    manager._tool_action_handler = None
    manager.logger = logging.getLogger("knowledge-scope-test")
    wrapped = manager._wrap_tool_with_dependencies(tool_info)
    wrapped.name = tool_info.name
    return ToolNode([wrapped])


def _tool_graph(tool_node):
    from airunner_services.llm.workflow_manager import WorkflowState
    import airunner_services.llm.managers.mixins.tool_execution_mixin as module

    module.WorkflowState = WorkflowState
    graph = StateGraph(WorkflowState)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("tools")
    graph.add_edge("tools", END)
    return graph.compile()


def _call(tool_name, args, call_id="call"):
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": tool_name,
                        "args": args,
                        "id": call_id,
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }


class _StubEmbedding:
    """Deterministic query embedding: everything matches the owner vector."""

    def embed_query(self, _query):
        return [1.0, 0.0]


def _scoped_agent(store, owner_path, other_path):
    """Real numpy retriever behind a minimal agent ``search`` surface."""
    from airunner_services.llm.managers.agent.retriever import (
        DocumentIndexRetriever,
    )
    from airunner_services.llm.managers.agent.vector_index import (
        DocumentVectorIndex,
    )

    index = DocumentVectorIndex(
        documents=[
            LangDocument(
                page_content="owner fact: the garden opens at dawn",
                metadata={
                    "doc_id": _persistent_id(str(owner_path)),
                    "source": str(owner_path),
                },
            ),
            LangDocument(
                page_content="other fact: the harbor closes at dusk",
                metadata={
                    "doc_id": _persistent_id(str(other_path)),
                    "source": str(other_path),
                },
            ),
        ],
        embeddings=np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
    )
    assert str(store) in str(owner_path)
    retriever = DocumentIndexRetriever(index, _StubEmbedding(), similarity_top_k=5)

    def search(query, k=3, doc_ids=None):
        del query
        return retriever.retrieve(query="scoped recall", doc_ids=doc_ids)[:k]

    agent = SimpleNamespace(search=search)
    return agent


def test_tool_schemas_hide_config(isolated_knowledge_base, monkeypatch):
    """Visible ToolNode schemas keep the legacy memory-tool contracts."""
    expected = {
        "record_knowledge": {"fact", "section"},
        "recall_knowledge": {"query", "max_results"},
        "update_knowledge": {"find_text", "replace_text", "date", "is_regex"},
        "delete_knowledge": {"text", "date", "is_regex"},
        "read_knowledge_file": {"date", "read_all"},
        "list_knowledge_files": set(),
    }
    for name, fields in expected.items():
        node = _tool_node(name, SimpleNamespace(), monkeypatch)
        schema = node.tools_by_name[name].get_input_schema().model_fields
        assert set(schema) == fields, name


def test_recall_empty_scope_returns_before_search_or_index(
    isolated_knowledge_base, monkeypatch
):
    """An explicitly empty scope stays empty without search/index/DB work."""
    from airunner_services import knowledge as knowledge_module

    def unexpected_search(*_args, **_kwargs):
        raise AssertionError("empty scope must return before searching")

    def unexpected_base():
        raise AssertionError("empty scope must return before loading the store")

    monkeypatch.setattr(
        knowledge_module.KnowledgeBase, "search_rag", unexpected_search
    )
    monkeypatch.setattr(knowledge_module, "get_knowledge_base", unexpected_base)

    @contextmanager
    def unexpected_session():
        raise AssertionError("empty scope must return before database access")
        yield

    monkeypatch.setattr(
        "airunner_services.database.session.session_scope", unexpected_session
    )

    node = _tool_node("recall_knowledge", SimpleNamespace(), monkeypatch)
    result = _tool_graph(node).invoke(
        _call("recall_knowledge", {"query": "garden"}),
        config={"configurable": {"rag_document_scope": ()}},
    )
    assert "No knowledge found for: 'garden'." in result["messages"][-1].content


def test_recall_scoped_rag_path_uses_request_doc_ids(
    isolated_knowledge_base, monkeypatch
):
    """Scoped recall searches only indexed content for its document IDs."""

    store = isolated_knowledge_base.store
    owner_path = store / "owner-note.md"
    other_path = store / "other-note.md"
    owner_path.write_text("# owner\n", encoding="utf-8")
    other_path.write_text("# other\n", encoding="utf-8")
    agent = _scoped_agent(store, owner_path, other_path)

    indexed_calls = []

    def unexpected_index(_files):
        indexed_calls.append(True)
        raise AssertionError("recall must not trigger explicit ingestion")

    monkeypatch.setattr(
        agent, "ensure_indexed_files", unexpected_index, raising=False
    )

    @contextmanager
    def unexpected_session():
        raise AssertionError("scoped recall must not touch the database")
        yield

    monkeypatch.setattr(
        "airunner_services.database.session.session_scope", unexpected_session
    )

    owner_scope = (_persistent_id(str(owner_path)),)
    other_scope = (_persistent_id(str(other_path)),)
    node = _tool_node("recall_knowledge", agent, monkeypatch)
    graph = _tool_graph(node)

    owner_text = graph.invoke(
        _call("recall_knowledge", {"query": "garden"}),
        config={"configurable": {"rag_document_scope": owner_scope}},
    )["messages"][-1].content
    assert "garden opens at dawn" in owner_text
    assert "harbor closes at dusk" not in owner_text

    other_text = graph.invoke(
        _call("recall_knowledge", {"query": "harbor"}),
        config={"configurable": {"rag_document_scope": other_scope}},
    )["messages"][-1].content
    assert "harbor closes at dusk" in other_text
    assert "garden opens at dawn" not in other_text
    assert indexed_calls == []


def test_scoped_recall_does_not_fall_back_to_keyword_store(
    isolated_knowledge_base, monkeypatch
):
    """A scoped request never widens past its document set via keywords."""
    kb = isolated_knowledge_base.kb
    assert kb.add_fact("the garden opens at dawn", section="Notes") is True

    node = _tool_node("recall_knowledge", SimpleNamespace(), monkeypatch)
    result = _tool_graph(node).invoke(
        _call("recall_knowledge", {"query": "garden"}),
        config={"configurable": {
            "rag_document_scope": ("00000000000000000000000000000000",),
            "chatbot_id": 7,
        }},
    )
    assert "No knowledge found for: 'garden'." in result["messages"][-1].content


def test_parallel_recalls_keep_scopes_isolated(
    isolated_knowledge_base, monkeypatch
):
    """Concurrent ToolNode recalls keep per-request scopes isolated."""
    store = isolated_knowledge_base.store
    owner_path = store / "owner-note.md"
    other_path = store / "other-note.md"
    owner_path.write_text("# owner\n", encoding="utf-8")
    other_path.write_text("# other\n", encoding="utf-8")
    agent = _scoped_agent(store, owner_path, other_path)

    graph = _tool_graph(_tool_node("recall_knowledge", agent, monkeypatch))

    def invoke(query, path):
        return graph.invoke(
            _call("recall_knowledge", {"query": query}),
            config={"configurable": {"rag_document_scope": (_persistent_id(str(path)),)}},
        )["messages"][-1].content

    with ThreadPoolExecutor(max_workers=2) as pool:
        owner = pool.submit(invoke, "garden", owner_path)
        other = pool.submit(invoke, "harbor", other_path)
        owner_text = owner.result(timeout=30)
        other_text = other.result(timeout=30)
    assert "garden opens at dawn" in owner_text
    assert "harbor closes at dusk" not in owner_text
    assert "harbor closes at dusk" in other_text
    assert "garden opens at dawn" not in other_text


def test_record_persists_across_instances_and_recall_finds_it(
    isolated_knowledge_base, monkeypatch
):
    """A recorded fact survives a store reload and is recallable by ToolNode."""
    from airunner_services import knowledge as knowledge_module
    from airunner_services.knowledge import KnowledgeBase

    @contextmanager
    def unexpected_session():
        raise AssertionError("memory tools must not touch the database")
        yield

    monkeypatch.setattr(
        "airunner_services.database.session.session_scope", unexpected_session
    )

    record_node = _tool_node("record_knowledge", SimpleNamespace(), monkeypatch)
    recorded = _tool_graph(record_node).invoke(
        _call("record_knowledge", {"fact": "User gardens at dawn"})
    )["messages"][-1].content
    assert "Recorded in Notes" in recorded

    fresh = KnowledgeBase(knowledge_dir=isolated_knowledge_base.store)
    monkeypatch.setattr(knowledge_module, "get_knowledge_base", lambda: fresh)
    recall_node = _tool_node("recall_knowledge", SimpleNamespace(), monkeypatch)
    found = _tool_graph(recall_node).invoke(
        _call("recall_knowledge", {"query": "gardens"})
    )["messages"][-1].content
    assert "User gardens at dawn" in found


def test_scoped_write_without_identity_rejected_before_write(
    isolated_knowledge_base, monkeypatch
):
    """Scoped writes without chatbot identity never touch the store."""
    store = isolated_knowledge_base.store
    config = {"configurable": {"rag_document_scope": ("some-doc-id",)}}

    record = _tool_graph(
        _tool_node("record_knowledge", SimpleNamespace(), monkeypatch)
    ).invoke(
        _call("record_knowledge", {"fact": "orphan fact"}), config=config
    )["messages"][-1].content
    assert "no chatbot ownership identity" in record

    update = _tool_graph(
        _tool_node("update_knowledge", SimpleNamespace(), monkeypatch)
    ).invoke(
        _call("update_knowledge", {
            "find_text": "anything", "replace_text": "else",
        }),
        config=config,
    )["messages"][-1].content
    assert "no chatbot ownership identity" in update

    delete = _tool_graph(
        _tool_node("delete_knowledge", SimpleNamespace(), monkeypatch)
    ).invoke(
        _call("delete_knowledge", {"text": "anything"}), config=config
    )["messages"][-1].content
    assert "no chatbot ownership identity" in delete

    assert list(store.iterdir()) == []


def test_invalid_inputs_rejected_before_write(isolated_knowledge_base, monkeypatch):
    """Empty patterns and escaping dates never mutate the store."""
    kb = isolated_knowledge_base.kb
    assert kb.add_fact("the garden opens at dawn", section="Notes") is True
    before = (kb._get_today_path()).read_bytes()

    record = _tool_graph(
        _tool_node("record_knowledge", SimpleNamespace(), monkeypatch)
    ).invoke(_call("record_knowledge", {"fact": "   "}))["messages"][-1].content
    assert "must not be empty" in record

    update_node = _tool_graph(
        _tool_node("update_knowledge", SimpleNamespace(), monkeypatch)
    )
    for args in (
        {"find_text": "", "replace_text": "else"},
        {"find_text": "", "replace_text": "else", "is_regex": True},
    ):
        response = update_node.invoke(_call("update_knowledge", args))[
            "messages"
        ][-1].content
        assert "must not be empty" in response

    delete = _tool_graph(
        _tool_node("delete_knowledge", SimpleNamespace(), monkeypatch)
    ).invoke(_call("delete_knowledge", {"text": ""}))["messages"][-1].content
    assert "must not be empty" in delete

    for tool_name, args in (
        ("read_knowledge_file", {"date": "../../escape"}),
        ("read_knowledge_file", {"date": "not-a-date"}),
        ("update_knowledge", {
            "find_text": "garden", "replace_text": "park",
            "date": "2025-13-99",
        }),
        ("delete_knowledge", {"text": "garden", "date": "../other.md"}),
    ):
        response = _tool_graph(
            _tool_node(tool_name, SimpleNamespace(), monkeypatch)
        ).invoke(_call(tool_name, args))["messages"][-1].content
        assert "invalid knowledge date" in response, (tool_name, args)

    assert kb._get_today_path().read_bytes() == before
    assert "escape" not in os.listdir(isolated_knowledge_base.store.parent)


def test_write_failure_preserves_existing_content(
    isolated_knowledge_base, monkeypatch
):
    """A failed record reports the error and keeps the previous file."""
    from airunner_services import knowledge as knowledge_module

    kb = isolated_knowledge_base.kb
    assert kb.add_fact("the garden opens at dawn", section="Notes") is True
    before = kb._get_today_path().read_bytes()

    def fail_write(_path, _content):
        raise OSError("synthetic write failure")

    monkeypatch.setattr(knowledge_module, "_write_text_atomically", fail_write)
    response = _tool_graph(
        _tool_node("record_knowledge", SimpleNamespace(), monkeypatch)
    ).invoke(_call("record_knowledge", {"fact": "a new fact"}))[
        "messages"
    ][-1].content
    assert "Error" in response
    assert kb._get_today_path().read_bytes() == before


def test_request_scope_routes_recall_through_workflow_config(
    isolated_knowledge_base, managed_sqlite_database, monkeypatch
):
    """The production request pipeline scopes ToolNode recall per chatbot."""
    from airunner_services.llm.managers.mixins.request_handling_mixin import (
        RequestHandlingMixin,
    )
    from airunner_services.llm.managers.mixins.streaming_mixin import (
        StreamingMixin,
    )

    db = managed_sqlite_database
    store = isolated_knowledge_base.store
    owner_path = store / "owner-note.md"
    other_path = store / "other-note.md"
    owner_path.write_text("# owner\n", encoding="utf-8")
    other_path.write_text("# other\n", encoding="utf-8")

    with db.session_module.session_scope() as session:
        owner = db.chatbot_model(name="Scope owner")
        other = db.chatbot_model(name="Scope other")
        session.add_all([owner, other])
        session.flush()
        owner_id, other_id = owner.id, other.id
        session.add_all(
            [
                db.document_model(path=str(owner_path), active=True, indexed=False),
                db.document_model(path=str(other_path), active=True, indexed=False),
            ]
        )
        session.flush()
        session.add(
            db.target_files_model(chatbot_id=owner_id, file_path=str(owner_path))
        )

    class ScopeOwner(RequestHandlingMixin):
        def __init__(self, chatbot_id):
            self.chatbot = SimpleNamespace(id=chatbot_id)

    owner_scope = RequestHandlingMixin._request_rag_document_scope(
        ScopeOwner(owner_id), SimpleNamespace(rag_files=None)
    )
    other_scope = RequestHandlingMixin._request_rag_document_scope(
        ScopeOwner(other_id), SimpleNamespace(rag_files=None)
    )
    assert owner_scope == (_persistent_id(str(owner_path)),)
    assert other_scope == ()

    @contextmanager
    def unexpected_session():
        raise AssertionError("scoped recall must not query the database")
        yield

    monkeypatch.setattr(
        "airunner_services.database.session.session_scope", unexpected_session
    )

    agent = _scoped_agent(store, owner_path, other_path)
    graph = _tool_graph(_tool_node("recall_knowledge", agent, monkeypatch))

    def workflow_config(chatbot_id, scope):
        workflow = object.__new__(StreamingMixin)
        workflow._thread_id = "scope-route-test"
        workflow.chatbot = SimpleNamespace(id=chatbot_id)
        config = workflow._create_config()
        assert config["configurable"]["chatbot_id"] == chatbot_id
        return {
            "configurable": {
                **config["configurable"],
                "rag_document_scope": scope,
            }
        }

    owner_text = graph.invoke(
        _call("recall_knowledge", {"query": "garden"}),
        config=workflow_config(owner_id, owner_scope),
    )["messages"][-1].content
    assert "garden opens at dawn" in owner_text
    assert "harbor closes at dusk" not in owner_text

    other_text = graph.invoke(
        _call("recall_knowledge", {"query": "garden"}),
        config=workflow_config(other_id, other_scope),
    )["messages"][-1].content
    assert "No knowledge found for: 'garden'." in other_text
