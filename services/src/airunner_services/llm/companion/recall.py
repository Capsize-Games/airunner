"""Shared recall contracts: citations, ranking pool, repo default (B05).

``fact_recall.py`` (record/recall/update/retract) and
``turn_recall.py`` (past-turn recall) build on this module. Scope is
enforced by the repository queries, never by prompt convention;
every recalled item carries its source ID (``[fact:7]`` /
``[turn:12]``).

Import submodules directly; none is re-exported from the package
``__init__``. Runtime imports stay light (no SQLAlchemy, no numpy,
no torch).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from .contracts import ChatbotId, SessionId, TurnId
from .memory_repository import FactRecord, TurnRecord

# Ranking reads a bounded candidate pool, not a full-table scan.
RANK_POOL_SIZE = 50
# Read-modify-write window for fact management (B14 lists beyond).
MANAGE_POOL_SIZE = 1000
# Query tokens shorter than this are ignored when ranking.
MIN_KEYWORD_LEN = 3


class CitedFact(BaseModel):
    """One recalled fact with its source ID attached."""

    model_config = ConfigDict(extra="forbid")

    fact_id: int
    chatbot_id: ChatbotId
    content: str
    subject: Optional[str] = None
    source: Optional[str] = None
    source_turn_id: Optional[TurnId] = None
    score: Optional[float] = None


class CitedTurn(BaseModel):
    """One recalled past turn with its source ID attached."""

    model_config = ConfigDict(extra="forbid")

    turn_id: int
    chatbot_id: ChatbotId
    session_id: SessionId
    role: str
    content: str
    turn_index: Optional[int] = None
    score: Optional[float] = None


def default_repository() -> object:
    """Return the scoped companion memory repository (lazy import)."""
    from .repository import SqlCompanionMemoryRepository

    return SqlCompanionMemoryRepository()


_BOUND: Dict[int, Tuple[Any, Any]] = {}


def bind_chatbot_index(chatbot_id: int, index: Any, client: Any) -> None:
    """Bind one chatbot's own B04 index plus its embedding client."""
    _BOUND[int(chatbot_id)] = (index, client)


def unbind_chatbot_index(chatbot_id: int) -> None:
    """Drop one chatbot's index binding (recall falls back cleanly)."""
    _BOUND.pop(int(chatbot_id), None)


def unbind_all_chatbot_indexes() -> None:
    """Drop every index binding (tests, daemon reload)."""
    _BOUND.clear()


def bound_chatbot_ids() -> List[int]:
    """Return the chatbot IDs with a bound recall index."""
    return sorted(_BOUND)


def get_bound_index(chatbot_id: int) -> Tuple[Any, Any]:
    """Return one chatbot's bound (index, client), or (None, None)."""
    pair: Optional[Tuple[Any, Any]] = _BOUND.get(int(chatbot_id))
    if pair is None:
        return None, None
    return pair


def fact_citation(fact_id: int) -> str:
    """Render one fact's citation (``[fact:7]``)."""
    return f"[fact:{int(fact_id)}]"


def turn_citation(turn_id: int) -> str:
    """Render one turn's citation (``[turn:12]``)."""
    return f"[turn:{int(turn_id)}]"


def format_cited_facts(facts: List[CitedFact], query: str = "") -> str:
    """Render cited facts for a tool reply or prompt."""
    if not facts:
        if query:
            return f"No stored facts match: '{query}'."
        return "No stored facts yet."
    lines = [f"Found {len(facts)} fact(s):", ""]
    for position, fact in enumerate(facts, 1):
        lines.append(
            f"{position}. {fact.content} {fact_citation(fact.fact_id)}"
        )
    return "\n".join(lines)


def format_cited_turns(turns: List[CitedTurn], query: str = "") -> str:
    """Render cited turns for a tool reply or prompt."""
    if not turns:
        if query:
            return f"No past turns match: '{query}'."
        return "No past turns yet."
    lines = [f"Found {len(turns)} turn(s):", ""]
    for position, turn in enumerate(turns, 1):
        lines.append(
            f"{position}. [{turn.role}] {turn.content} "
            f"{turn_citation(turn.turn_id)}"
        )
    return "\n".join(lines)


def keyword_score(query: str, text: str) -> float:
    """Fraction of the query's tokens appearing in the text."""
    tokens = [t for t in query.lower().split() if len(t) >= MIN_KEYWORD_LEN]
    if not tokens:
        return 0.0
    lowered = text.lower()
    hits = sum(1 for token in tokens if token in lowered)
    return hits / len(tokens)


def cited_fact(row: FactRecord, score: Optional[float]) -> CitedFact:
    """Attach a citation to one stored fact row."""
    if row.fact_id is None:
        raise ValueError("stored fact has no fact_id")
    return CitedFact(
        fact_id=int(row.fact_id),
        chatbot_id=row.chatbot_id,
        content=row.content,
        subject=getattr(row, "subject", None),
        source=getattr(row, "source", None),
        source_turn_id=row.source_turn_id,
        score=score,
    )


def cited_turn(row: TurnRecord, score: Optional[float]) -> CitedTurn:
    """Attach a citation to one stored turn row."""
    if row.turn_id is None:
        raise ValueError("stored turn has no turn_id")
    return CitedTurn(
        turn_id=int(row.turn_id),
        chatbot_id=row.chatbot_id,
        session_id=row.session_id,
        role=row.role,
        content=row.content,
        turn_index=row.turn_index,
        score=score,
    )


__all__ = [
    "MANAGE_POOL_SIZE",
    "MIN_KEYWORD_LEN",
    "RANK_POOL_SIZE",
    "CitedFact",
    "CitedTurn",
    "bind_chatbot_index",
    "bound_chatbot_ids",
    "cited_fact",
    "cited_turn",
    "default_repository",
    "fact_citation",
    "format_cited_facts",
    "format_cited_turns",
    "get_bound_index",
    "keyword_score",
    "turn_citation",
    "unbind_all_chatbot_indexes",
    "unbind_chatbot_index",
]
