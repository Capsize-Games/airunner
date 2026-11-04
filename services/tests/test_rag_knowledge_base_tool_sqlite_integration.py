"""Real SQLite ORM round trip for request-scoped knowledge saves."""

from __future__ import annotations

import hashlib
import logging
import os
from types import SimpleNamespace

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
import pytest


@pytest.fixture
def managed_sqlite_database(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", f"sqlite:///{tmp_path / 'service.sqlite3'}")
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
            path_settings_model=PathSettings,
            target_files_model=TargetFiles,
            managed_root=tmp_path / "managed",
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


def _tool_node(tool_name, rag_manager, monkeypatch):
    import airunner_services.api.runtime as api_runtime
    from airunner_services.llm.tool_manager import ToolManager

    from airunner_services.llm.core.tool_registry import ToolRegistry

    monkeypatch.setattr(
        api_runtime,
        "get_api",
        lambda: rag_manager,
    )
    tool_info = ToolRegistry.get(tool_name)
    manager = object.__new__(ToolManager)
    manager.rag_manager = rag_manager
    manager._request_tool_defaults = {}
    manager._tool_action_handler = None
    manager.logger = logging.getLogger("rag-real-sqlite-test")
    wrapped = manager._wrap_tool_with_dependencies(tool_info)
    wrapped.name = tool_info.name
    return ToolNode([wrapped])


def _tool_input(tool_name, args, call_id):
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


def _tool_graph(tool_node):
    from airunner_services.llm.workflow_manager import WorkflowState
    import airunner_services.llm.managers.mixins.tool_execution_mixin as module

    module.WorkflowState = WorkflowState
    graph = StateGraph(WorkflowState)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("tools")
    graph.add_edge("tools", END)
    return graph.compile()


def _persistent_id(path):
    canonical = os.path.normpath(os.path.abspath(path))
    return hashlib.md5(canonical.encode()).hexdigest()


def test_toolnode_save_commits_chatbot_assignment_and_isolates_catalog_scope(
    managed_sqlite_database, monkeypatch
):
    from airunner_services.database.models.document import Document
    from airunner_services.database.models.path_settings import PathSettings
    from airunner_services.database.models.target_files import TargetFiles
    from airunner_services.llm.managers.mixins.request_handling_mixin import (
        RequestHandlingMixin,
    )

    db = managed_sqlite_database
    db.managed_root.mkdir(mode=0o700)
    with db.session_module.session_scope() as session:
        owner = db.chatbot_model(name="SQLite owner")
        other = db.chatbot_model(name="SQLite other")
        settings = db.path_settings_model(base_path=str(db.managed_root))
        session.add_all([owner, other, settings])
        session.flush()
        owner_id, other_id = owner.id, other.id

    assert PathSettings.objects.first().base_path == str(db.managed_root)

    rag_manager = SimpleNamespace()
    save_node = _tool_node("save_to_knowledge_base", rag_manager, monkeypatch)
    save_output = _tool_graph(save_node).invoke(
        _tool_input(
            "save_to_knowledge_base",
            {
                "content": "persisted only for owner",
                "title": "sqlite scoped note",
                "category": "research",
            },
            "save-sqlite",
        ),
        config={"configurable": {"chatbot_id": owner_id}},
    )
    message = save_output["messages"][-1].content
    assert "saved and registered" in message

    saved_path = (
        db.managed_root
        / "knowledge_base"
        / "research"
        / "sqlite_scoped_note.txt"
    )
    assert saved_path.read_text() == (
        "Title: sqlite scoped note\n"
        "Category: research\n\n---\n\n"
        "persisted only for owner"
    )

    # The save path uses real Object managers and commits. Reset the cached
    # session/engine and reopen records as a separate request/process would.
    db.session_module.reset_engine()
    with db.session_module.session_scope() as session:
        registered = session.query(Document).filter_by(path=str(saved_path)).one()
        assignment = (
            session.query(TargetFiles)
            .filter_by(chatbot_id=owner_id, file_path=str(saved_path))
            .one()
        )
        assert registered.active is True
        assert registered.indexed is False
        assert assignment.file_path == registered.path

    class ScopeOwner(RequestHandlingMixin):
        def __init__(self, chatbot_id):
            self.chatbot = SimpleNamespace(id=chatbot_id)

    owner_scope = RequestHandlingMixin._request_rag_document_scope(
        ScopeOwner(owner_id), SimpleNamespace(rag_files=None)
    )
    other_scope = RequestHandlingMixin._request_rag_document_scope(
        ScopeOwner(other_id), SimpleNamespace(rag_files=None)
    )
    assert owner_scope == (_persistent_id(str(saved_path)),)
    assert other_scope == ()

    search_node = _tool_node("search_knowledge_base_documents", rag_manager, monkeypatch)
    search_graph = _tool_graph(search_node)
    owner_search = search_graph.invoke(
        _tool_input(
            "search_knowledge_base_documents",
            {"query": "sqlite scoped note"},
            "search-owner",
        ),
        config={"configurable": {"rag_document_scope": owner_scope}},
    )["messages"][-1].content
    other_search = search_graph.invoke(
        _tool_input(
            "search_knowledge_base_documents",
            {"query": "sqlite scoped note"},
            "search-other",
        ),
        config={"configurable": {"rag_document_scope": other_scope}},
    )["messages"][-1].content
    assert "sqlite_scoped_note.txt" in owner_search
    assert "sqlite_scoped_note.txt" not in other_search
