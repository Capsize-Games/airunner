"""Legacy migration sources and the migration target contract (B14).

Builds stable, content-independent identities for legacy file
knowledge and legacy conversations, and scans both without modifying
the originals. Markdown parsing lives in ``knowledge.py`` (which
owns the format); this module only maps it onto migration inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable

from airunner_services.knowledge import (
    knowledge_source_identity,
    parse_knowledge_facts,
)

from .contracts import CallChainId, ChatbotId
from .memory_repository import FactRecord, SessionRecord, TurnRecord


@dataclass(frozen=True)
class LegacyFact:
    """One parsed fact line with its stable event identity."""

    event_id: str
    section: str
    text: str


@dataclass(frozen=True)
class LegacyKnowledgeFile:
    """One scanned legacy markdown file and its parsed facts."""

    identity: str
    tenant: str
    filename: str
    checksum: str
    facts: tuple[LegacyFact, ...]


@dataclass(frozen=True)
class LegacyMessage:
    """One normalized legacy conversation message."""

    role: str
    content: str


@dataclass(frozen=True)
class LegacyConversation:
    """One legacy conversation row shaped for migration."""

    identity: str
    conversation_id: int
    chatbot_id: int | None
    checksum: str
    messages: tuple[LegacyMessage, ...]


def fact_event_id(source_identity: str, index: int) -> str:
    """Return one stable fact identity within a source."""
    return f"{source_identity}#fact:{index}"


def turn_call_chain_id(source_identity: str, index: int) -> CallChainId:
    """Return one stable turn identity within a source."""
    return CallChainId(f"{source_identity}#turn:{index}")


def conversation_identity(conversation_id: int) -> str:
    """Return one stable identity preserving a conversation ID."""
    return f"conversation:{conversation_id}"


def checksum_text(text: str) -> str:
    """Return the hex SHA-256 digest of one string."""
    return sha256(text.encode("utf-8")).hexdigest()


def iter_knowledge_files(root: Path) -> Iterator[tuple[str, Path]]:
    """Yield ``(tenant, path)`` for legacy markdown, sorted.

    Top-level files predate tenant scoping and yield an empty
    tenant; ``tenants/<name>/*.md`` yields that tenant name. A
    missing root yields nothing: there is simply nothing to do.
    """
    if not root.is_dir():
        return
    for path in sorted(root.glob("*.md")):
        yield "", path
    tenants = root / "tenants"
    if not tenants.is_dir():
        return
    for path in sorted(tenants.glob("*/*.md")):
        yield path.parent.name, path


def scan_knowledge_file(tenant: str, path: Path) -> LegacyKnowledgeFile:
    """Read one legacy file without modifying it."""
    text = path.read_text(encoding="utf-8")
    identity = knowledge_source_identity(tenant, path.name)
    facts = tuple(
        LegacyFact(fact_event_id(identity, i), section, fact)
        for i, (section, fact) in enumerate(parse_knowledge_facts(text))
    )
    return LegacyKnowledgeFile(
        identity, tenant, path.name, checksum_text(text), facts
    )


def scan_knowledge_directory(root: Path) -> list[LegacyKnowledgeFile]:
    """Scan one knowledge directory; originals are only read."""
    return [
        scan_knowledge_file(tenant, path)
        for tenant, path in iter_knowledge_files(root)
    ]


def _normalize_message(entry: object) -> LegacyMessage | None:
    """Coerce one legacy message dict, or None when unusable."""
    if not isinstance(entry, dict):
        return None
    content = str(entry.get("content", "") or "")
    if not content.strip():
        return None
    role = "assistant" if entry.get("is_bot") else "user"
    return LegacyMessage(role, content)


def normalize_conversation_messages(
    value: object,
) -> tuple[LegacyMessage, ...]:
    """Coerce a legacy conversation payload to role/content pairs.

    Matches the stored ``Conversation.value`` shape; anything else
    yields no messages rather than raising on old data.
    """
    if not isinstance(value, list):
        return ()
    return tuple(
        m for m in (_normalize_message(e) for e in value) if m is not None
    )


def legacy_conversation(
    conversation_id: int,
    chatbot_id: int | None,
    value: object,
) -> LegacyConversation:
    """Build one migration input from a legacy conversation row."""
    identity = conversation_identity(conversation_id)
    messages = normalize_conversation_messages(value)
    canonical = "\n".join(f"{m.role}:{m.content}" for m in messages)
    checksum = checksum_text(f"{conversation_id}\n{canonical}")
    return LegacyConversation(
        identity, conversation_id, chatbot_id, checksum, messages
    )


class MigratedFactRecord(FactRecord):
    """One migrated fact carrying its stable provenance.

    The extra fields mirror StoredFactRecord (repository.py), which
    the real SQL repository reads via getattr, so migrated facts
    flow through it with event_id as the idempotency key.
    """

    subject: str | None = None
    source: str | None = None
    event_id: str | None = None


@runtime_checkable
class MigrationTarget(Protocol):
    """The scoped-repository surface one migration run writes to.

    Narrower than CompanionMemoryRepository on purpose: migration
    only appends facts and turns, so fakes implement three methods
    instead of the full repository contract.
    """

    def upsert_fact(self, fact: FactRecord) -> FactRecord:
        """Insert one fact idempotently by its event identity."""
        ...

    def get_or_start_session(self, chatbot_id: ChatbotId) -> SessionRecord:
        """Return one chatbot's session for migrated turns."""
        ...

    def append_turn(self, turn: TurnRecord) -> TurnRecord:
        """Append one migrated turn idempotently by call chain."""
        ...


__all__ = [
    "LegacyConversation",
    "LegacyFact",
    "LegacyKnowledgeFile",
    "LegacyMessage",
    "MigratedFactRecord",
    "MigrationTarget",
    "checksum_text",
    "conversation_identity",
    "fact_event_id",
    "iter_knowledge_files",
    "legacy_conversation",
    "normalize_conversation_messages",
    "scan_knowledge_directory",
    "scan_knowledge_file",
    "turn_call_chain_id",
]
