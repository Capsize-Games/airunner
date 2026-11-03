"""Request-provided RAG document filters stay explicit and immutable."""

import numpy as np
import logging
import threading
from contextlib import contextmanager
from langchain_core.documents import Document
from types import SimpleNamespace
import pytest

from airunner_services.llm.managers.mixins.request_handling_mixin import (
    RequestHandlingMixin,
)
from airunner_services.llm.managers.agent.retriever import DocumentIndexRetriever
from airunner_services.llm.managers.agent.retriever import MultiIndexRetriever
from airunner_services.llm.managers.agent.vector_index import DocumentVectorIndex


class _Embedding:
    def embed_query(self, _query):
        return [1.0, 0.0]


def test_document_retriever_distinguishes_absent_empty_and_selected_scope():
    index = DocumentVectorIndex(
        documents=[
            Document(page_content="alpha", metadata={"doc_id": "alpha"}),
            Document(page_content="beta", metadata={"doc_id": "beta"}),
        ],
        embeddings=np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
    )
    retriever = DocumentIndexRetriever(index, _Embedding(), similarity_top_k=2)

    assert [doc.page_content for doc in retriever.retrieve("query")] == [
        "alpha",
        "beta",
    ]
    assert retriever.retrieve("query", doc_ids=()) == []
    assert [
        doc.page_content for doc in retriever.retrieve("query", doc_ids=("beta",))
    ] == ["beta"]

    restricted = DocumentIndexRetriever(
        index, _Embedding(), similarity_top_k=2, doc_ids=("alpha",)
    )
    assert restricted.retrieve("query", doc_ids=("beta",)) == []
    assert [
        doc.page_content
        for doc in restricted.retrieve("query", doc_ids=("alpha",))
    ] == ["alpha"]
    no_embed = type(
        "NoEmbed",
        (),
        {"embed_query": lambda *_args: (_ for _ in ()).throw(AssertionError())},
    )()
    assert MultiIndexRetriever(
        type("Rag", (), {"embedding": no_embed})()
    ).retrieve("query", doc_ids=()) == []


def test_request_handling_passes_each_chatbot_scope_to_generation(monkeypatch):
    from airunner_services.database.models.target_files import TargetFiles

    paths = ("/docs/a.txt", "/docs/b.txt")
    target_rows = [
        SimpleNamespace(chatbot_id=11, file_path=paths[0]),
        SimpleNamespace(chatbot_id=22, file_path=paths[1]),
    ]
    document_rows = [SimpleNamespace(path=path) for path in paths]

    class _Query:
        def __init__(self, rows):
            self.rows = rows
            self.criteria = {}
            self.expression = None

        def filter_by(self, **criteria):
            self.criteria = criteria
            return self

        def filter(self, expression):
            self.expression = expression
            return self

        def all(self):
            rows = self.rows
            if self.criteria:
                rows = [
                    row for row in rows
                    if all(getattr(row, key) == value for key, value in self.criteria.items())
                ]
            if self.expression is not None:
                selected_paths = set(self.expression.right.value)
                rows = [row for row in rows if row.path in selected_paths]
            return rows

    class _Session:
        def query(self, model):
            return _Query(target_rows if model is TargetFiles else document_rows)

    @contextmanager
    def session_scope():
        yield _Session()

    monkeypatch.setattr("airunner_services.database.session.session_scope", session_scope)

    class _Manager(RequestHandlingMixin):
        def __init__(self, chatbot_id):
            self.chatbot = SimpleNamespace(id=chatbot_id)
            self.logger = logging.getLogger("request-rag-scope-test")
            self._request_state_lock = threading.RLock()
            self._current_request_id = None
            self._interrupted = False
            self._chat_model = None
            self._workflow_manager = None

        def _invalidate_setting_cache(self, _model):
            pass

        def _apply_request_overrides(self, _request):
            return False

        def _do_set_seed(self):
            pass

        def load(self):
            pass

        def _request_tool_defaults(self, _data):
            return None

        def _prepare_request_memory(self, _request):
            pass

        def _prepare_request_conversation(self, _data, _request):
            pass

        def _prepare_request_tooling(self, _data, _request):
            return False, [], None

        def _prepare_request_rag(self, _data, _request, _categories):
            return ()

        def _apply_request_thinking_override(self, _request):
            return []

        def _apply_request_reasoning_effort_override(self, _request):
            return []

        def _restore_thinking_patches(self, _patches):
            pass

        def _restore_reasoning_effort_patches(self, _patches):
            pass

        def _do_generate(self, **kwargs):
            return {"scope": kwargs["rag_document_scope"]}

    def run(chatbot_id):
        manager = _Manager(chatbot_id)
        return manager.handle_request(
            {
                "request_id": f"bot-{chatbot_id}",
                "request_data": {
                    "prompt": "query",
                    "action": "chat",
                    "llm_request": SimpleNamespace(rag_files=None),
                },
            }
        )["scope"]

    scope_a = run(11)
    scope_b = run(22)
    assert len(scope_a) == len(scope_b) == 1
    assert set(scope_a).isdisjoint(scope_b)

    request_only_owner = type("Owner", (), {"chatbot": None})()
    request_only = RequestHandlingMixin._request_rag_document_scope(
        request_only_owner,
        SimpleNamespace(rag_files=[paths[0]]),
        uploaded_document_ids=("uploaded-id",),
    )
    import hashlib
    import os

    expected_request_id = hashlib.md5(os.path.abspath(paths[0]).encode()).hexdigest()
    assert set(request_only) == {expected_request_id, "uploaded-id"}


def test_request_rag_failure_restores_request_overrides(monkeypatch):
    restored = []

    monkeypatch.setattr(
        "airunner_services.llm.managers.mixins.request_handling_mixin.capture_request_settings_snapshot",
        lambda _manager: {"fixture": "snapshot"},
    )
    monkeypatch.setattr(
        "airunner_services.llm.managers.mixins.request_handling_mixin.restore_request_settings_snapshot",
        lambda _manager, snapshot: restored.append(snapshot),
    )

    class _Manager(RequestHandlingMixin):
        def __init__(self):
            self._request_state_lock = threading.RLock()
            self._current_request_id = None
            self._interrupted = False
            self._chat_model = None
            self._workflow_manager = None
            self._tool_manager = None
            self.logger = logging.getLogger("request-rag-error-cleanup-test")
            self.unload_calls = 0

        def _invalidate_setting_cache(self, _model):
            pass

        def _apply_request_overrides(self, _request):
            return True

        def unload(self):
            self.unload_calls += 1

        def _do_set_seed(self):
            pass

        def load(self):
            pass

        def _request_tool_defaults(self, _data):
            return None

        def _prepare_request_memory(self, _request):
            pass

        def _prepare_request_conversation(self, _data, _request):
            pass

        def _prepare_request_tooling(self, _data, _request):
            return False, [], None

        def _prepare_request_rag(self, _data, _request, _categories):
            raise ValueError("selected RAG document is unsupported")

        def _do_generate(self, **_kwargs):
            pytest.fail("generation must not run after RAG preparation fails")

    manager = _Manager()
    with pytest.raises(ValueError, match="selected RAG document"):
        manager.handle_request(
            {
                "request_id": "invalid-rag-selection",
                "request_data": {
                    "prompt": "question",
                    "action": "chat",
                    "llm_request": SimpleNamespace(rag_files=["bad.docx"]),
                },
            }
        )

    assert restored == [{"fixture": "snapshot"}]
    assert manager.unload_calls == 2
