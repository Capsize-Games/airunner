"""Scoped fact record/recall/update/retract (release B05).

Facts persist through the B01 repository and rank through the B04
index (vector path) or keyword overlap (no-index path). Candidates
always come from the scoped repository: a hit naming another
chatbot, or no stored row, is dropped, never returned. Retraction
is a state change (B03), never a row deletion.

Import this submodule directly; it is not re-exported from the
package ``__init__``. Runtime imports stay light (no SQLAlchemy,
no numpy, no torch).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .contracts import ChatbotId
from .memory_repository import FactRecord
from .recall import (
    MANAGE_POOL_SIZE,
    RANK_POOL_SIZE,
    CitedFact,
    cited_fact,
    keyword_score,
)

if TYPE_CHECKING:
    from .embeddings import CompanionEmbeddingClient
    from .embeddings import CompanionEmbeddingIndex
    from .repository import SqlCompanionMemoryRepository


def record_fact(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    content: str,
    subject: Optional[str] = None,
    source: str = "companion-tool",
    event_id: Optional[str] = None,
    index: Optional["CompanionEmbeddingIndex"] = None,
    client: Optional["CompanionEmbeddingClient"] = None,
) -> CitedFact:
    """Store one fact for one chatbot; optionally index its text."""
    stored = repository.upsert_fact(
        _new_fact(chatbot_id, content, subject, source, event_id)
    )
    if index is not None and client is not None:
        index_fact(index, client, stored)
    return cited_fact(stored, None)


def recall_facts(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    query: str,
    limit: int = 5,
    index: Optional["CompanionEmbeddingIndex"] = None,
    client: Optional["CompanionEmbeddingClient"] = None,
) -> List[CitedFact]:
    """Return this chatbot's facts ranked for ``query``, cited."""
    if limit <= 0:
        return []
    if index is not None and client is not None and query.strip():
        ranked = _recall_vector(
            repository, chatbot_id, query, limit, index, client
        )
        if ranked:
            return ranked
    return _recall_keyword(repository, chatbot_id, query, limit)


def update_fact(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    fact_id: int,
    content: str,
) -> CitedFact:
    """Replace one fact's content, keeping citation and provenance."""
    current = _scoped_fact_row(repository, chatbot_id, fact_id)
    stored = repository.upsert_fact(_updated_fact(current, content))
    return cited_fact(stored, None)


def retract_fact(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    fact_id: int,
    reason: Optional[str] = None,
) -> CitedFact:
    """Retract one fact without deleting its row (reopenable)."""
    stored = repository.retract_fact(chatbot_id, int(fact_id), reason=reason)
    return cited_fact(stored, None)


def index_fact(
    index: "CompanionEmbeddingIndex",
    client: "CompanionEmbeddingClient",
    fact: FactRecord,
) -> None:
    """Add one stored fact's text to the chatbot's own index."""
    if fact.fact_id is None:
        raise ValueError("cannot index a fact with no fact_id")
    index.add_texts(
        [fact.content],
        client,
        metadatas=[
            {
                "kind": "fact",
                "fact_id": int(fact.fact_id),
                "chatbot_id": int(fact.chatbot_id),
            }
        ],
    )


def _new_fact(
    chatbot_id: ChatbotId,
    content: str,
    subject: Optional[str],
    source: str,
    event_id: Optional[str],
) -> FactRecord:
    """Build the storable record (lazy: keeps this module light)."""
    from .repository import StoredFactRecord

    return StoredFactRecord(
        chatbot_id=chatbot_id,
        content=content,
        subject=subject,
        source=source,
        event_id=event_id,
    )


def _updated_fact(current: FactRecord, content: str) -> FactRecord:
    """Rebuild one row with new content, provenance preserved."""
    from .repository import StoredFactRecord

    return StoredFactRecord(
        fact_id=current.fact_id,
        chatbot_id=current.chatbot_id,
        content=content,
        source_turn_id=current.source_turn_id,
        confidence=current.confidence,
        metadata=dict(current.metadata),
        subject=getattr(current, "subject", None),
        source=getattr(current, "source", None),
        event_id=getattr(current, "event_id", None),
    )


def _scoped_fact_row(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    fact_id: int,
) -> FactRecord:
    """Return one chatbot's fact row or raise (scope enforced)."""
    for row in repository.get_facts(chatbot_id, limit=MANAGE_POOL_SIZE):
        if row.fact_id == int(fact_id):
            return row
    raise ValueError(f"No fact {fact_id} for chatbot {chatbot_id}")


def _recall_vector(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    query: str,
    limit: int,
    index: "CompanionEmbeddingIndex",
    client: "CompanionEmbeddingClient",
) -> List[CitedFact]:
    """Rank scoped facts by embedding similarity (B04 index)."""
    pool = max(limit, RANK_POOL_SIZE)
    rows = _rows_by_id(repository, chatbot_id, pool)
    ranked: List[CitedFact] = []
    for hit in index.search(query, client, k=pool):
        joined = _join_hit(hit, rows, chatbot_id)
        if joined is not None:
            ranked.append(joined)
        if len(ranked) >= limit:
            break
    return ranked


def _rows_by_id(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    pool: int,
) -> Dict[Any, FactRecord]:
    """Index one chatbot's candidate facts by fact ID."""
    return {
        row.fact_id: row
        for row in repository.get_facts(chatbot_id, limit=pool)
    }


def _join_hit(
    hit: Any, rows: Dict[Any, FactRecord], chatbot_id: ChatbotId
) -> Optional[CitedFact]:
    """Join one index hit to a scoped row, or drop it (never leak)."""
    metadata = getattr(hit, "metadata", None) or {}
    if int(metadata.get("chatbot_id", -1)) != int(chatbot_id):
        return None
    row = rows.get(metadata.get("fact_id"))
    if row is None:
        return None
    return cited_fact(row, float(getattr(hit, "score", 0.0)))


def _recall_keyword(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    query: str,
    limit: int,
) -> List[CitedFact]:
    """Rank scoped facts by keyword overlap (no-index path)."""
    pool = repository.get_facts(chatbot_id, limit=max(limit, RANK_POOL_SIZE))
    if not query.strip():
        return [cited_fact(row, None) for row in pool[:limit]]
    scored = [(row, keyword_score(query, row.content)) for row in pool]
    matched = [(row, score) for row, score in scored if score > 0]
    matched.sort(key=lambda item: item[1], reverse=True)
    return [cited_fact(row, score) for row, score in matched[:limit]]


__all__ = [
    "index_fact",
    "recall_facts",
    "record_fact",
    "retract_fact",
    "update_fact",
]
