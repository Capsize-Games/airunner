"""Regression tests for release issue B05.

Proves scoped fact record/recall/update/retract and past-turn
recall through the B01 repository and B04 retrieval:

- Neutral fixtures retrieve expected facts/turns with citations.
- Cross-chatbot queries cannot return another bot's data.
- Legacy tools stay registered via the documented compat adapter.

Uses explicit temporary SQLite databases, deterministic fake
embeddings, and a blocked socket layer: no real model, network,
GPU, or GUI access.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List

import pytest

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.session import reset_engine, session_scope
from airunner_services.database.setup_database import setup_database
from airunner_services.llm.companion.contracts import (
    ERROR_EMBEDDING_SPACE_MISMATCH,
    CallChainId,
    ChatbotId,
    CompanionError,
)
from airunner_services.llm.companion.embeddings import (
    CompanionEmbeddingIndex,
    EmbeddingModelIdentity,
)
from airunner_services.llm.companion.memory_repository import TurnRecord
from airunner_services.llm.companion import fact_recall
from airunner_services.llm.companion import recall as companion_recall
from airunner_services.llm.companion import turn_recall
from airunner_services.llm.companion.repository import (
    SqlCompanionMemoryRepository,
)
from airunner_services.llm.core.tool_registry import ToolRegistry
from airunner_services.llm.tools import companion_memory_compat as compat
from airunner_services.llm.tools import companion_memory_tools as tools

_DIM = 8


class FakeEmbeddingClient:
    """Deterministic hash embeddings: same text, same vector."""

    def __init__(self, identity: EmbeddingModelIdentity) -> None:
        self._identity = identity

    @property
    def identity(self) -> EmbeddingModelIdentity:
        return self._identity

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vector(text)

    def _vector(self, text: str) -> List[float]:
        dim = int(self._identity.dimension)
        out: List[float] = []
        block = 0
        while len(out) < dim:
            digest = hashlib.sha256(f"b05:{block}:{text}".encode()).digest()
            out.extend(byte / 127.5 - 1.0 for byte in digest)
            block += 1
        return out[:dim]


def _identity(**overrides: Any) -> EmbeddingModelIdentity:
    base: Dict[str, Any] = {
        "model_id": "b05-fake",
        "revision": "main",
        "dimension": _DIM,
    }
    base.update(overrides)
    return EmbeddingModelIdentity(**base)


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'release-b05.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    tools.unbind_all_chatbot_indexes()
    yield db_url
    tools.unbind_all_chatbot_indexes()
    reset_engine()


@pytest.fixture()
def repo() -> SqlCompanionMemoryRepository:
    return SqlCompanionMemoryRepository()


def _make_chatbot(name: str) -> ChatbotId:
    with session_scope() as db:
        chatbot = Chatbot(name=f"{name}-{datetime.now().timestamp()}")
        db.add(chatbot)
        db.flush()
        return ChatbotId(chatbot.id)


def _bind(chatbot_id: ChatbotId) -> FakeEmbeddingClient:
    client = FakeEmbeddingClient(_identity())
    tools.bind_chatbot_index(
        int(chatbot_id), CompanionEmbeddingIndex(client.identity), client
    )
    return client


def _record_indexed(repo, chatbot_id, content, subject=None):
    index, client = tools.get_bound_index(int(chatbot_id))
    return fact_recall.record_fact(
        repo,
        chatbot_id,
        content,
        subject=subject,
        index=index,
        client=client,
    )


def _append_turn(repo, chatbot_id, session_id, role, content, chain):
    return repo.append_turn(
        TurnRecord(
            chatbot_id=chatbot_id,
            session_id=session_id,
            role=role,
            content=content,
            call_chain_id=CallChainId(chain),
        )
    )


# --- Record/recall round trip with citations ---


def test_record_and_recall_preserve_citations(test_db, repo) -> None:
    bot = _make_chatbot("bot-a")
    _bind(bot)
    first = _record_indexed(repo, bot, "the library lends telescopes")
    _record_indexed(repo, bot, "the ferry horn means boarding")

    facts = fact_recall.recall_facts(
        repo, bot, "the library lends telescopes", limit=2
    )
    assert [fact.content for fact in facts][0] == (
        "the library lends telescopes"
    )
    assert facts[0].fact_id == first.fact_id
    assert facts[0].score == pytest.approx(1.0)

    rendered = companion_recall.format_cited_facts(facts, query="library")
    assert f"[fact:{first.fact_id}]" in rendered


def test_keyword_recall_without_index_ranks_match_first(test_db, repo) -> None:
    bot = _make_chatbot("bot-a")
    fact_recall.record_fact(repo, bot, "the community garden opens at dawn")
    fact_recall.record_fact(repo, bot, "the ferry horn means boarding")

    facts = fact_recall.recall_facts(repo, bot, "ferry horn", limit=5)
    assert [fact.content for fact in facts] == [
        "the ferry horn means boarding"
    ]
    assert (
        fact_recall.recall_facts(repo, bot, "telescope zebra", limit=5) == []
    )
    assert "No stored facts match" in companion_recall.format_cited_facts(
        [], query="telescope zebra"
    )


def test_update_fact_keeps_citation_and_provenance(test_db, repo) -> None:
    bot = _make_chatbot("bot-a")
    stored = fact_recall.record_fact(
        repo, bot, "the library opens at noon", subject="library"
    )
    updated = fact_recall.update_fact(
        repo, bot, stored.fact_id, "the library opens at dawn"
    )
    assert updated.fact_id == stored.fact_id
    assert updated.content == "the library opens at dawn"
    assert updated.subject == "library"

    facts = fact_recall.recall_facts(repo, bot, "library dawn", limit=5)
    assert [fact.content for fact in facts] == ["the library opens at dawn"]


def test_retract_fact_removes_from_recall_but_keeps_row(test_db, repo) -> None:
    bot = _make_chatbot("bot-a")
    stored = fact_recall.record_fact(
        repo, bot, "the ferry horn means boarding"
    )
    cited = fact_recall.retract_fact(
        repo, bot, stored.fact_id, reason="superseded"
    )
    assert cited.fact_id == stored.fact_id
    assert fact_recall.recall_facts(repo, bot, "ferry", limit=5) == []
    retracted = repo.get_facts(bot, limit=10, include_retracted=True)
    assert [fact.fact_id for fact in retracted] == [stored.fact_id]


def test_past_turn_recall_returns_cited_turns(test_db, repo) -> None:
    bot = _make_chatbot("bot-a")
    session = repo.get_or_start_session(bot)
    assert session.session_id is not None
    _append_turn(
        repo,
        bot,
        session.session_id,
        "user",
        "do you lend telescopes",
        "cc-b05-1",
    )
    asked = _append_turn(
        repo,
        bot,
        session.session_id,
        "assistant",
        "yes, the library lends telescopes",
        "cc-b05-2",
    )

    turns = turn_recall.recall_turns(
        repo, bot, session.session_id, query="library lends", limit=5
    )
    assert [turn.turn_id for turn in turns] == [asked.turn_id]
    assert turns[0].role == "assistant"
    assert turns[0].turn_index is not None
    rendered = companion_recall.format_cited_turns(turns, query="library")
    assert f"[turn:{asked.turn_id}]" in rendered

    recent = turn_recall.recall_turns(repo, bot, session.session_id, limit=5)
    assert [turn.content for turn in recent] == [
        "do you lend telescopes",
        "yes, the library lends telescopes",
    ]


def test_vector_turn_recall_uses_bound_index(test_db, repo) -> None:
    bot = _make_chatbot("bot-a")
    client = _bind(bot)
    index, _ = tools.get_bound_index(int(bot))
    session = repo.get_or_start_session(bot)
    assert session.session_id is not None
    _append_turn(
        repo,
        bot,
        session.session_id,
        "user",
        "the garden opens at dawn",
        "cc-b05-3",
    )
    target = _append_turn(
        repo,
        bot,
        session.session_id,
        "user",
        "the ferry horn means boarding",
        "cc-b05-4",
    )
    for turn in repo.get_recent_turns(bot, session.session_id, limit=10):
        turn_recall.index_turn(index, client, turn)

    turns = turn_recall.recall_turns(
        repo,
        bot,
        session.session_id,
        query="the ferry horn means boarding",
        limit=2,
        index=index,
        client=client,
    )
    assert turns[0].turn_id == target.turn_id
    assert turns[0].score == pytest.approx(1.0)


# --- Chatbot scope ---


def test_cross_bot_recall_update_retract_are_isolated(test_db, repo) -> None:
    bot_a = _make_chatbot("bot-a")
    bot_b = _make_chatbot("bot-b")
    stored = fact_recall.record_fact(
        repo, bot_a, "the library lends telescopes"
    )

    assert (
        fact_recall.recall_facts(repo, bot_b, "library telescopes", limit=5)
        == []
    )
    assert fact_recall.recall_facts(repo, bot_b, "", limit=5) == []
    with pytest.raises(ValueError):
        fact_recall.update_fact(
            repo, bot_b, stored.fact_id, "hijacked content"
        )
    with pytest.raises(ValueError):
        fact_recall.retract_fact(repo, bot_b, stored.fact_id)

    intact = fact_recall.recall_facts(
        repo, bot_a, "library telescopes", limit=5
    )
    assert [fact.content for fact in intact] == [
        "the library lends telescopes"
    ]


def test_foreign_index_hits_are_dropped_never_leaked(test_db, repo) -> None:
    bot_a = _make_chatbot("bot-a")
    bot_b = _make_chatbot("bot-b")
    client_a = FakeEmbeddingClient(_identity())
    index_a = CompanionEmbeddingIndex(client_a.identity)
    fact_recall.record_fact(
        repo,
        bot_a,
        "the library lends telescopes",
        index=index_a,
        client=client_a,
    )
    fact_recall.record_fact(repo, bot_b, "the garden opens at dawn")

    # A caller passing the wrong chatbot's index gets no foreign rows:
    # hits naming bot A cannot join bot B's scoped candidates, so the
    # vector path yields nothing and keyword fallback ranks B only.
    facts = fact_recall.recall_facts(
        repo,
        bot_b,
        "library telescopes",
        limit=5,
        index=index_a,
        client=client_a,
    )
    assert all("telescopes" not in fact.content for fact in facts)
    assert all(fact.chatbot_id == int(bot_b) for fact in facts)


def test_embedding_space_mismatch_raises_not_misleads(test_db, repo) -> None:
    bot = _make_chatbot("bot-a")
    client = FakeEmbeddingClient(_identity())
    index = CompanionEmbeddingIndex(client.identity)
    fact_recall.record_fact(
        repo,
        bot,
        "the library lends telescopes",
        index=index,
        client=client,
    )
    foreign = FakeEmbeddingClient(_identity(dimension=4))
    with pytest.raises(CompanionError) as excinfo:
        fact_recall.recall_facts(
            repo, bot, "library", limit=5, index=index, client=foreign
        )
    assert excinfo.value.error.code == ERROR_EMBEDDING_SPACE_MISMATCH


# --- Registered tools and the compatibility adapter ---


def test_new_tools_registered_and_scoped(test_db) -> None:
    for name in (
        "record_companion_fact",
        "recall_companion_facts",
        "update_companion_fact",
        "retract_companion_fact",
        "recall_companion_turns",
    ):
        assert ToolRegistry.get(name) is not None, name

    bot_a = _make_chatbot("bot-a")
    bot_b = _make_chatbot("bot-b")
    reply = tools.record_companion_fact(
        int(bot_a), "the ferry horn means boarding"
    )
    assert reply.startswith("Recorded [fact:")

    found = tools.recall_companion_facts(int(bot_a), "ferry horn")
    assert "ferry horn means boarding" in found
    assert "[fact:" in found
    assert "No stored facts match" in tools.recall_companion_facts(
        int(bot_b), "ferry horn"
    )

    other = tools.recall_companion_turns(int(bot_b), 9999)
    assert "No past turns yet." in other


def test_legacy_tools_available_through_documented_adapter(
    test_db,
) -> None:
    for legacy in compat.legacy_tool_names():
        assert ToolRegistry.get(legacy) is not None, legacy
        assert ToolRegistry.get(compat.resolve_legacy_tool(legacy)) is not None
    for legacy in compat.UNMAPPED_LEGACY_TOOLS:
        assert ToolRegistry.get(legacy) is not None, legacy
    with pytest.raises(KeyError):
        compat.resolve_legacy_tool("list_knowledge_files")

    bot_a = _make_chatbot("bot-a")
    bot_b = _make_chatbot("bot-b")
    assert "Recorded [fact:" in compat.adapt_legacy_tool(
        "record_knowledge", int(bot_a), "the garden opens at dawn", "Notes"
    )
    assert "garden opens at dawn" in compat.recall_knowledge_scoped(
        int(bot_a), "garden dawn"
    )
    assert "No stored facts match" in compat.recall_knowledge_scoped(
        int(bot_b), "garden dawn"
    )
    assert "Updated [fact:" in compat.update_knowledge_scoped(
        int(bot_a), "opens at dawn", "opens at sunrise"
    )
    assert "garden opens at sunrise" in compat.read_knowledge_scoped(
        int(bot_a)
    )
    assert "Retracted 1 fact(s)" in compat.delete_knowledge_scoped(
        int(bot_a), "garden opens"
    )
    assert "No stored facts match" in compat.recall_knowledge_scoped(
        int(bot_a), "garden"
    )
    assert "Text not found" in compat.update_knowledge_scoped(
        int(bot_a), "missing text", "replacement"
    )


def test_legacy_conversation_tools_map_to_cited_turns(test_db, repo) -> None:
    bot = _make_chatbot("bot-a")
    session = repo.get_or_start_session(bot)
    assert session.session_id is not None
    _append_turn(
        repo,
        bot,
        session.session_id,
        "user",
        "the garden opens at dawn",
        "cc-b05-5",
    )
    assert compat.resolve_legacy_tool("get_conversation_summary") == (
        "recall_companion_turns"
    )
    assert compat.resolve_legacy_tool("load_conversation") == (
        "recall_companion_turns"
    )
    summary = compat.conversation_summary_scoped(
        int(bot), int(session.session_id)
    )
    assert "garden opens at dawn" in summary
    assert "[turn:" in summary
    assert "garden opens at dawn" in compat.load_conversation_scoped(
        int(bot), int(session.session_id)
    )


# --- Offline and import hygiene ---


def test_scoped_memory_makes_no_external_transport_call(
    test_db, repo, monkeypatch
) -> None:
    import socket

    def _blocked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("external transport call attempted")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    bot = _make_chatbot("bot-a")
    client = FakeEmbeddingClient(_identity())
    index = CompanionEmbeddingIndex(client.identity)
    stored = fact_recall.record_fact(
        repo,
        bot,
        "the library lends telescopes",
        index=index,
        client=client,
    )
    assert fact_recall.recall_facts(
        repo, bot, "library", limit=5, index=index, client=client
    )
    fact_recall.update_fact(repo, bot, stored.fact_id, "updated")
    fact_recall.retract_fact(repo, bot, stored.fact_id)
    session = repo.get_or_start_session(bot)
    assert session.session_id is not None
    turn_recall.recall_turns(repo, bot, session.session_id, limit=5)
    assert tools.recall_companion_facts(int(bot), "library")


def test_recall_module_imports_without_heavy_deps() -> None:
    """Recall modules stay light: no sqlalchemy/numpy/torch/redis/Qt."""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; before = set(sys.modules); "
            "from airunner_services.llm.companion import fact_recall; "
            "from airunner_services.llm.companion import turn_recall; "
            "after = set(sys.modules); new = after - before; "
            "markers = 'sqlalchemy,numpy,torch,redis,PySide6'; "
            "markers += ',PyQt'; marks = markers.split(','); "
            "hits = [m for m in new for mk in marks if mk in m.lower()]; "
            "print(','.join(hits)); sys.exit(1 if hits else 0)",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout
