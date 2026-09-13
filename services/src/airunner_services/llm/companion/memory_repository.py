"""Scoped memory repository contract for the Desktop companion (B01).

An interface only — B03 implements this against Desktop's own SQLAlchemy
models (new tables, not a reuse of any web/UwUchat table), B02 persists
sessions/turns, B07-B09 write through it for facts/episodic summaries/
rolling compression, and B05 reads through it for recall tools.

Every method is scoped by ``ChatbotId`` (and, where relevant,
``SessionId``): a companion component must never be able to read or
write another chatbot's memory by construction, not by convention. This
mirrors the per-user scoping already enforced by the RAG/knowledge tools
inventoried in W01 (facts are per-chatbot there too), and matches the
existing Desktop pattern of scoping persistence to one owning entity
(see e.g. the tenant-key scoping in ``airunner_services.data.tenant``).

Frozen upstream shape this maps to (W01,
https://github.com/Capsize-Games/airunnerweb/blob/8157628a.../wiki/Desktop-Bot-Port-Reference.md
§3): ``ChatSession`` (id, chatbot_id, user_id, started_at,
last_message_at, episodic_summary, rolling_summary, emotional_weight,
key_topics, summary_ready) and ``ConversationTurn`` (id, chatbot_id,
session_id, conversation_id, role, content, embedding_enc, turn_index,
call_chain_id, created_at). Desktop is single-user and local-only, so
``user_id`` is dropped; per-user encryption-at-rest (upstream) is an
explicit open question for B02/B03 to resolve with the owner, not
assumed here either way (see W01 §7).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from .contracts import CallChainId, ChatbotId, SessionId, TurnId


class TurnRecord(BaseModel):
    """One persisted conversation turn.

    Field names deliberately match upstream ``ConversationTurn``
    (W01 §3) minus ``embedding_enc`` (no separately-stored embedding
    column; B04 owns the embeddings index) and minus
    ``conversation_id``. Upstream UwUchat has no multi-conversation
    concept (W01 §2), but Desktop *does* --
    ``src/airunner/components/conversations/`` (``ConversationRecord``,
    ``ConversationHistoryManager``) lets one chatbot have several
    conversations. Whether a companion session/turn should map onto
    that existing model, or remain a separate companion-specific
    concept, is an open question left for B02/B03 (see
    companion-contracts.md §4), not an erased assumption (release issue
    B01 review finding F9).

    ``turn_index`` is assigned by ``append_turn`` (like ``turn_id``),
    not supplied by the caller: a caller composing a turn only sees a
    windowed, size-limited "recent turns" list (see
    ``get_recent_turns``' ``limit``), which is not a reliable source for
    a session's true, monotonically increasing turn count once a
    session has more turns than that window.
    """

    model_config = ConfigDict(extra="forbid")

    turn_id: Optional[TurnId] = None
    chatbot_id: ChatbotId
    session_id: SessionId
    role: str
    content: str
    turn_index: Optional[int] = None
    call_chain_id: CallChainId


class SessionRecord(BaseModel):
    """One conversation session (a bounded span of turns).

    ``rolling_summary``/``episodic_summary``/``emotional_weight``/
    ``key_topics``/``summary_ready`` match upstream ``ChatSession``
    field-for-field (W01 §3) since B08/B09 write exactly these.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: Optional[SessionId] = None
    chatbot_id: ChatbotId
    started_at: str
    last_message_at: str
    episodic_summary: Optional[str] = None
    rolling_summary: Optional[str] = None
    emotional_weight: Optional[float] = None
    key_topics: List[str] = Field(default_factory=list)
    summary_ready: bool = False


class FactRecord(BaseModel):
    """One stored fact (B03/B07)."""

    model_config = ConfigDict(extra="forbid")

    fact_id: Optional[int] = None
    chatbot_id: ChatbotId
    content: str
    source_turn_id: Optional[TurnId] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class CompanionMemoryRepository(Protocol):
    """Scoped read/write access to one chatbot's companion memory.

    A concrete implementation (B03) owns its own transaction/session
    handling; methods here are request/response shaped so they compose
    cleanly whether the backing store is sync or async underneath (B03
    decides, this contract does not).
    """

    def get_or_start_session(
        self, chatbot_id: ChatbotId
    ) -> SessionRecord:
        """Return the chatbot's active session, starting one if needed.

        Session-rotation policy (the upstream 4-hour-gap rule from W01
        §2, or a different threshold) is a B02 implementation decision,
        not fixed by this contract.
        """
        ...

    def append_turn(self, turn: TurnRecord) -> TurnRecord:
        """Persist one completed turn; returns it with ``turn_id`` and
        ``turn_index`` set (the latter assigned from the session's true
        total turn count, not merely a caller-visible recent-turns
        window -- see ``TurnRecord``)."""
        ...

    def get_recent_turns(
        self, chatbot_id: ChatbotId, session_id: SessionId, *, limit: int
    ) -> List[TurnRecord]:
        """Return the most recent turns for one session, oldest first."""
        ...

    def update_session_summary(self, session: SessionRecord) -> None:
        """Persist an updated rolling/episodic summary for one session.

        Called by B08 (episodic) and B09 (rolling compression); both
        write through this one method rather than separate ones so a
        future storage change touches one call site.
        """
        ...

    def get_facts(
        self, chatbot_id: ChatbotId, *, limit: int
    ) -> List[FactRecord]:
        """Return known facts for one chatbot, most relevant/recent first.

        Ranking policy is a B03 implementation decision.
        """
        ...

    def upsert_fact(self, fact: FactRecord) -> FactRecord:
        """Insert or update one fact; B07 owns dedup policy before this
        call, not this method (a repository does not decide whether two
        facts are "the same fact")."""
        ...


__all__ = [
    "CompanionMemoryRepository",
    "FactRecord",
    "SessionRecord",
    "TurnRecord",
]
