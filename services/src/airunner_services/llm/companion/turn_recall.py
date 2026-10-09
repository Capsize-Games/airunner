"""Scoped past-turn recall (release B05).

Turns persist through the B02 repository path (``append_turn`` --
this module only reads) and rank through the B04 index (vector
path) or keyword overlap (no-index path). Candidates always come
from the scoped repository: a hit naming another chatbot, or no
stored row, is dropped, never returned. An empty query returns the
most recent turns in chronological order; a query ranks best first.

Import this submodule directly; it is not re-exported from the
package ``__init__``. Runtime imports stay light (no SQLAlchemy,
no numpy, no torch).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .contracts import ChatbotId, SessionId
from .memory_repository import TurnRecord
from .recall import RANK_POOL_SIZE, CitedTurn, cited_turn, keyword_score

if TYPE_CHECKING:
    from .embeddings import CompanionEmbeddingClient
    from .embeddings import CompanionEmbeddingIndex
    from .repository import SqlCompanionMemoryRepository


def recall_turns(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    session_id: SessionId,
    query: str = "",
    limit: int = 5,
    index: Optional["CompanionEmbeddingIndex"] = None,
    client: Optional["CompanionEmbeddingClient"] = None,
) -> List[CitedTurn]:
    """Return one session's past turns, cited (ranked when queried)."""
    if limit <= 0:
        return []
    if index is not None and client is not None and query.strip():
        ranked = _recall_vector(
            repository, chatbot_id, session_id, query, limit, index, client
        )
        if ranked:
            return ranked
    return _recall_keyword(repository, chatbot_id, session_id, query, limit)


def index_turn(
    index: "CompanionEmbeddingIndex",
    client: "CompanionEmbeddingClient",
    turn: TurnRecord,
) -> None:
    """Add one stored turn's text to the chatbot's own index."""
    if turn.turn_id is None:
        raise ValueError("cannot index a turn with no turn_id")
    index.add_texts(
        [turn.content],
        client,
        metadatas=[
            {
                "kind": "turn",
                "turn_id": int(turn.turn_id),
                "chatbot_id": int(turn.chatbot_id),
            }
        ],
    )


def _recall_vector(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    session_id: SessionId,
    query: str,
    limit: int,
    index: "CompanionEmbeddingIndex",
    client: "CompanionEmbeddingClient",
) -> List[CitedTurn]:
    """Rank one session's turns by embedding similarity (B04)."""
    pool = max(limit, RANK_POOL_SIZE)
    rows = _rows_by_id(repository, chatbot_id, session_id, pool)
    ranked: List[CitedTurn] = []
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
    session_id: SessionId,
    pool: int,
) -> Dict[Any, TurnRecord]:
    """Index one session's candidate turns by turn ID."""
    return {
        row.turn_id: row
        for row in repository.get_recent_turns(
            chatbot_id, session_id, limit=pool
        )
    }


def _join_hit(
    hit: Any, rows: Dict[Any, TurnRecord], chatbot_id: ChatbotId
) -> Optional[CitedTurn]:
    """Join one index hit to a scoped turn, or drop it (never leak)."""
    metadata = getattr(hit, "metadata", None) or {}
    if int(metadata.get("chatbot_id", -1)) != int(chatbot_id):
        return None
    row = rows.get(metadata.get("turn_id"))
    if row is None:
        return None
    return cited_turn(row, float(getattr(hit, "score", 0.0)))


def _recall_keyword(
    repository: "SqlCompanionMemoryRepository",
    chatbot_id: ChatbotId,
    session_id: SessionId,
    query: str,
    limit: int,
) -> List[CitedTurn]:
    """Rank one session's turns by keyword overlap (no-index path)."""
    pool = repository.get_recent_turns(
        chatbot_id, session_id, limit=max(limit, RANK_POOL_SIZE)
    )
    if not query.strip():
        return [cited_turn(row, None) for row in pool[:limit]]
    scored = [(row, keyword_score(query, row.content)) for row in pool]
    matched = [(row, score) for row, score in scored if score > 0]
    matched.sort(key=lambda item: item[1], reverse=True)
    return [cited_turn(row, score) for row, score in matched[:limit]]


__all__ = [
    "index_turn",
    "recall_turns",
]
