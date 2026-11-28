"""Unit tests for the retriever extraction helpers.

_search_unified_index and _resolve_active_doc_ids were extracted to
keep retrieve() within the long-function threshold. These tests pin
the unified-index behavior, the scope filtering, and the distinct
silent/warned early-return paths.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.llm.managers.agent.retriever import (
    MultiIndexRetriever,
)


def _make_retriever(mixin, top_k=3):
    retriever = MultiIndexRetriever.__new__(MultiIndexRetriever)
    retriever._rag_mixin = mixin
    retriever._similarity_top_k = top_k
    return retriever


def _mixin(**overrides):
    mixin = SimpleNamespace()
    mixin.embedding = SimpleNamespace(verified_identity=None)
    mixin.logger = MagicMock()
    mixin._get_active_document_ids = MagicMock(return_value=["a", "b"])
    mixin._index = None
    for key, value in overrides.items():
        setattr(mixin, key, value)
    return mixin


def test_unified_search_skips_when_no_index():
    mixin = _mixin()
    retriever = _make_retriever(mixin)
    docs = []
    retriever._search_unified_index([0.1], None, None, docs)
    assert docs == []


def test_unified_search_extends_documents():
    mixin = _mixin()
    mixin._index = MagicMock()
    mixin._index.similarity_search_by_vector.return_value = ["hit"]
    retriever = _make_retriever(mixin)
    docs = []
    retriever._search_unified_index([0.1], "ident", ["a"], docs)
    assert docs == ["hit"]
    mixin._index.similarity_search_by_vector.assert_called_once()


def test_unified_search_swallows_errors():
    mixin = _mixin()
    mixin._index = MagicMock()
    mixin._index.similarity_search_by_vector.side_effect = RuntimeError("x")
    retriever = _make_retriever(mixin)
    docs = ["existing"]
    retriever._search_unified_index([0.1], None, None, docs)
    assert docs == ["existing"]


def test_resolve_scope_filters_by_allowed_ids():
    mixin = _mixin()
    retriever = _make_retriever(mixin)
    assert retriever._resolve_active_doc_ids(["a"]) == ["a"]


def test_resolve_scope_returns_none_when_filtered_empty():
    mixin = _mixin()
    retriever = _make_retriever(mixin)
    assert retriever._resolve_active_doc_ids(["zzz"]) is None
    mixin.logger.warning.assert_not_called()


def test_resolve_scope_warns_when_no_active_documents():
    mixin = _mixin(_get_active_document_ids=MagicMock(return_value=[]))
    retriever = _make_retriever(mixin)
    assert retriever._resolve_active_doc_ids(None) is None
    mixin.logger.warning.assert_called_once()


def test_retrieve_empty_explicit_scope_returns_empty():
    mixin = _mixin()
    mixin.embedding.embed_query = MagicMock(return_value=[0.1])
    retriever = _make_retriever(mixin)
    assert retriever.retrieve("q", doc_ids=[]) == []


def test_retrieve_no_embedding_returns_empty():
    mixin = _mixin()
    mixin.embedding.embed_query = MagicMock(return_value=None)
    retriever = _make_retriever(mixin)
    assert retriever.retrieve("q") == []
