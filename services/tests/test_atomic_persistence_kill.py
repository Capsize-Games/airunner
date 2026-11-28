"""Kill-between-writes persistence: staging file plus atomic rename.

Issue #2488: a crash (or kill) during a save must never leave a
truncated file behind, and save failures must surface to the caller
instead of being silently swallowed.
"""

from __future__ import annotations

import json
import logging
import os
from types import SimpleNamespace

import numpy as np
import pytest
from langchain_core.documents import Document

from airunner_services.knowledge import KnowledgeBase
from airunner_services.llm.managers.agent.mixins import (
    rag_index_management_mixin as management_mixin,
)
from airunner_services.llm.managers.agent.vector_index import DocumentVectorIndex


def _kill_between_write(source: str, destination: str) -> None:
    """Simulate a kill after staging a file but before its rename."""
    raise OSError("simulated kill between staging write and rename")


def test_vector_persist_kill_before_rename_preserves_old_files(
    tmp_path, monkeypatch
) -> None:
    """A kill before the first rename keeps the previous index intact."""
    target = tmp_path / "index"
    old = DocumentVectorIndex(
        [Document(page_content="old")],
        np.asarray([[1.0, 0.0]], dtype=np.float32),
    )
    old.persist(str(target))
    old_documents = (target / "documents.json").read_bytes()
    old_embeddings = (target / "embeddings.npy").read_bytes()

    new = DocumentVectorIndex(
        [Document(page_content="new")],
        np.asarray([[0.0, 1.0]], dtype=np.float32),
    )
    monkeypatch.setattr(
        "airunner_services.llm.managers.agent.vector_index"
        ".os.replace",
        _kill_between_write,
    )
    with pytest.raises(OSError, match="simulated kill"):
        new.persist(str(target))

    assert (target / "documents.json").read_bytes() == old_documents
    assert (target / "embeddings.npy").read_bytes() == old_embeddings
    loaded = DocumentVectorIndex.load(str(target))
    assert [doc.page_content for doc in loaded.documents] == ["old"]


def test_vector_persist_kill_mid_sequence_never_truncates(
    tmp_path, monkeypatch
) -> None:
    """A kill between file renames leaves no truncated file behind."""
    target = tmp_path / "index"
    old = DocumentVectorIndex(
        [Document(page_content="old")],
        np.asarray([[1.0, 0.0]], dtype=np.float32),
    )
    old.persist(str(target))

    # Two rows on purpose: after a mid-sequence kill the staged
    # documents no longer match the surviving embeddings, so the
    # mismatch must fail loudly instead of loading silently.
    new = DocumentVectorIndex(
        [Document(page_content="new-a"), Document(page_content="new-b")],
        np.asarray([[0.0, 1.0], [1.0, 1.0]], dtype=np.float32),
    )
    real_replace = os.replace
    calls = {"count": 0}

    def kill_on_second_rename(source: str, destination: str) -> None:
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("simulated kill between file renames")
        real_replace(source, destination)

    monkeypatch.setattr(
        "airunner_services.llm.managers.agent.vector_index"
        ".os.replace",
        kill_on_second_rename,
    )
    with pytest.raises(OSError, match="simulated kill"):
        new.persist(str(target))

    # Every surviving file still parses on its own: nothing truncated.
    json.loads((target / "documents.json").read_text(encoding="utf-8"))
    np.load(str(target / "embeddings.npy"), allow_pickle=False)
    with pytest.raises(ValueError, match="row counts do not match"):
        DocumentVectorIndex.load(str(target))


def test_knowledge_kill_before_rename_preserves_old_content(
    tmp_path, monkeypatch
) -> None:
    """A kill during a knowledge save keeps the previous file intact."""
    kb = KnowledgeBase(knowledge_dir=tmp_path)
    assert kb.add_fact("Alice prefers tea", section="Notes") is True
    today_path = kb._get_today_path()
    old_bytes = today_path.read_bytes()

    monkeypatch.setattr(
        "airunner_services.knowledge.os.replace",
        _kill_between_write,
    )
    with pytest.raises(OSError, match="simulated kill"):
        kb.add_fact("Bob prefers coffee", section="Notes")

    assert today_path.read_bytes() == old_bytes
    content = today_path.read_text(encoding="utf-8")
    assert "Alice prefers tea" in content
    assert "Bob prefers coffee" not in content


def test_registry_save_failure_raises_and_preserves(
    tmp_path, monkeypatch
) -> None:
    """A registry save failure raises instead of logging and swallowing."""
    registry_path = tmp_path / "index_registry.json"
    harness = SimpleNamespace(
        doc_indexes_dir=str(tmp_path),
        registry_path=str(registry_path),
        _index_registry={
            "documents": {"doc-1": {"path": "/tmp/source.txt"}},
            "version": "2.0",
        },
        logger=logging.getLogger("registry-kill-test"),
    )
    management_mixin.RAGIndexManagementMixin._save_registry(harness)
    old_bytes = registry_path.read_bytes()

    harness._index_registry = {"documents": {}, "version": "2.0"}
    monkeypatch.setattr(
        "airunner_services.llm.managers.agent.mixins"
        ".rag_index_management_mixin.os.replace",
        _kill_between_write,
    )
    with pytest.raises(OSError, match="simulated kill"):
        management_mixin.RAGIndexManagementMixin._save_registry(harness)

    assert registry_path.read_bytes() == old_bytes
    assert set(
        json.loads(registry_path.read_text(encoding="utf-8"))[
            "documents"
        ].keys()
    ) == {"doc-1"}
