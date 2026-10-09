"""Post-turn fact extraction and deduplication (release issue B07).

Ports upstream's ``llm/knowledge_extractor.py`` behavior (W01 §3) onto
B06 jobs, B03 facts, and B05 lookup/write helpers: after one
completed response turn, a bounded ``FACT_EXTRACTION`` job asks for
candidate facts, validates the model output schema, drops duplicates
and facts the turn does not support, applies corrections as
retract-then-save, and stores the rest idempotently.

Upstream rules ported (behavior only, no upstream source moved):

- Trigger input is the last user + assistant message pair.
- Subject vocabulary is ``user``/``self``/``world``.
- Corrections are handled first: retract the old wrong fact, then
  save the correct one.
- Dedup is two-layered: a KB similarity lookup first (here B05's
  ``recall_facts``, standing in for upstream's TF-IDF search), with
  an algorithmic normalized-text/overlap backstop that always runs.
- Retraction never deletes the row (B03 state change).

No model, network, or GPU I/O lives here. Inference runs through the
injected ``ExtractFn``, which the daemon wires to the local runtime
via the ``JobContext.arbitrate`` entry point (the same arbitration
interactive generation uses, per the B06 contract) -- this module
never loads a model instance of its own. Prompts are bounded by
``ContextBudget``. Import directly, never from ``__init__``
(SQLAlchemy, like ``repository.py``/``jobs.py``).
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from airunner_services.runtimes.contracts import ChatMessage, MessageRole

from .contracts import ChatbotId, ContextBudget, SessionId
from .jobs import JobContext, JobHandler
from .memory_repository import FactRecord, TurnRecord
from .recall import MANAGE_POOL_SIZE, keyword_score
from .repository import SqlCompanionMemoryRepository
from .scheduler import (
    CompanionJobHandle,
    CompanionJobRequest,
    CompanionJobType,
    CompanionScheduler,
)

_SYSTEM_PROMPT = (
    "Extract durable facts from the completed conversation turns "
    "below. Reply with facts only: each fact must be stated or "
    "clearly implied by the turns shown. Do not invent facts about "
    "people, places, or events not mentioned. Mark a fact for "
    "retraction only when a turn directly corrects or contradicts "
    "an already-known fact listed below."
)

_ROLE_MAP: Dict[str, MessageRole] = {
    "system": MessageRole.SYSTEM,
    "user": MessageRole.USER,
    "assistant": MessageRole.ASSISTANT,
}

# Rough chars-per-token so the prompt respects the token budget
# without a tokenizer dependency.
_CHARS_PER_TOKEN = 4

# A candidate sharing less of its significant tokens with the
# source turns than this is unsupported (invented) and rejected.
_MIN_GROUNDING_SCORE = 0.5

# A candidate matching a stored fact at or above this overlap is
# the same fact, not a new one.
_DUPLICATE_OVERLAP = 0.8

_WORD = re.compile(r"[a-z0-9]+")


class ExtractedFact(BaseModel):
    """One model-proposed fact write, schema-validated."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["save", "retract"] = "save"
    content: str = Field(min_length=1)
    subject: Literal["user", "self", "world"] = "user"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    """The validated model response for one extraction event."""

    model_config = ConfigDict(extra="forbid")

    facts: List[ExtractedFact] = Field(default_factory=list)


# May raise retryable CompanionError when inference is unavailable.
# The daemon wires this to the local runtime through the context's
# ``arbitrate`` entry point; tests pass a fake.
ExtractFn = Callable[[JobContext, List[ChatMessage]], ExtractionResult]


def normalize_fact_text(content: str) -> str:
    """Lowercase alphanumeric tokens, joined by single spaces."""
    return " ".join(_WORD.findall(content.lower()))


def is_supported(candidate: str, turn_text: str) -> bool:
    """True when the turns carry the candidate's significant tokens."""
    if not normalize_fact_text(candidate):
        return False
    return keyword_score(candidate, turn_text) >= _MIN_GROUNDING_SCORE


def is_same_fact(candidate: str, stored: str) -> bool:
    """True when two fact texts state the same fact."""
    left = normalize_fact_text(candidate)
    right = normalize_fact_text(stored)
    if not left or not right:
        return False
    if left == right:
        return True
    overlap = max(
        keyword_score(candidate, stored), keyword_score(stored, candidate)
    )
    return overlap >= _DUPLICATE_OVERLAP


def build_extraction_prompt(
    turns: List[TurnRecord],
    known_facts: List[FactRecord],
    budget: ContextBudget,
) -> List[ChatMessage]:
    """Render source turns plus known facts as bounded messages."""
    char_cap = budget.max_prompt_tokens * _CHARS_PER_TOKEN
    messages = [ChatMessage(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT)]
    # The fixed instruction is constant overhead; the cap bounds the
    # variable per-turn content (turns plus known facts).
    used = 0
    for turn in turns[-max(budget.max_recent_turns, 1) :]:
        role = _ROLE_MAP.get(turn.role)
        if role is None:
            continue
        body = turn.content[:char_cap] if char_cap > 0 else ""
        if used + len(body) > char_cap and char_cap > 0:
            body = body[: max(char_cap - used, 0)]
        used += len(body)
        messages.append(ChatMessage(role=role, content=body))
    for fact in known_facts[: max(budget.max_facts, 0)]:
        line = f"[fact:{fact.fact_id}] {fact.content}"
        if char_cap > 0 and used + len(line) > char_cap:
            break
        used += len(line)
        messages.append(ChatMessage(role=MessageRole.SYSTEM, content=line))
    return messages


def schedule_fact_extraction(
    scheduler: CompanionScheduler,
    *,
    chatbot_id: ChatbotId,
    session_id: SessionId,
    turn_id: int,
) -> CompanionJobHandle:
    """Schedule one extraction keyed to its completed turn."""
    return scheduler.schedule(
        CompanionJobRequest(
            job_type=CompanionJobType.FACT_EXTRACTION,
            chatbot_id=chatbot_id,
            session_id=session_id,
            idempotency_key=f"fact-extract:{turn_id}",
            payload={"turn_id": int(turn_id)},
        )
    )


def make_fact_extraction_handler(
    repository: SqlCompanionMemoryRepository,
    extract: ExtractFn,
    *,
    budget: Optional[ContextBudget] = None,
) -> JobHandler:
    """Build the B06 handler executing ``FACT_EXTRACTION`` jobs."""
    active = budget or ContextBudget()

    def _handle(context: JobContext) -> None:
        _run_extraction(repository, extract, context, active)

    return _handle


def _run_extraction(
    repository: SqlCompanionMemoryRepository,
    extract: ExtractFn,
    context: JobContext,
    budget: ContextBudget,
) -> None:
    """Extract one turn's facts; nothing is written before inference."""
    if context.session_id is None:
        raise ValueError("fact extraction job has no session_id")
    turns = _source_turns(repository, context, budget)
    if not turns:
        return
    known = repository.get_facts(context.chatbot_id, limit=MANAGE_POOL_SIZE)
    prompt = build_extraction_prompt(turns, known, budget)
    result = _validated(extract(context, prompt))
    _apply(repository, context, turns, known, result, budget)


def _validated(raw: object) -> ExtractionResult:
    """Re-validate one model response; malformed means no writes."""
    if isinstance(raw, ExtractionResult):
        return raw
    if isinstance(raw, dict):
        try:
            return ExtractionResult(**raw)
        except ValidationError as exc:
            raise ValueError(f"invalid extraction response: {exc}") from exc
    raise ValueError(f"invalid extraction response type: {type(raw).__name__}")


def _source_turns(
    repository: SqlCompanionMemoryRepository,
    context: JobContext,
    budget: ContextBudget,
) -> List[TurnRecord]:
    """The completed pair ending at the job's turn, oldest first."""
    assert context.session_id is not None  # guarded by _run_extraction
    pool = repository.get_recent_turns(
        context.chatbot_id, context.session_id, limit=MANAGE_POOL_SIZE
    )
    target = context.payload.get("turn_id")
    ordered = [t for t in pool if _is_completed(t)]
    if target is not None:
        ordered = [t for t in ordered if int(t.turn_id or -1) <= int(target)]
        if not any(int(t.turn_id or -1) == int(target) for t in ordered):
            return []
    width = max(min(budget.max_recent_turns, 2), 1)
    return ordered[-width:]


def _is_completed(turn: TurnRecord) -> bool:
    """True for a persisted turn with real content."""
    if turn.turn_id is None or turn.turn_index is None:
        return False
    return bool(turn.content.strip())


def _apply(
    repository: SqlCompanionMemoryRepository,
    context: JobContext,
    turns: List[TurnRecord],
    known: List[FactRecord],
    result: ExtractionResult,
    budget: ContextBudget,
) -> None:
    """Apply corrections first, then saves; skip dupes/unsupported."""
    from . import fact_recall

    text = "\n".join(t.content for t in turns)
    seen: List[str] = [f.content for f in known if f.fact_id is not None]
    capped = result.facts[: max(budget.max_facts, 0)]
    retracts = [f for f in capped if f.action == "retract"]
    saves = [f for f in capped if f.action == "save"]
    for item in retracts:
        withdrawn = _apply_retract(repository, context.chatbot_id, known, item)
        # A correction's replacement must not match the fact it
        # just withdrew as a "duplicate".
        seen = [text for text in seen if text != withdrawn]
    for position, item in enumerate(saves):
        _apply_save(
            fact_recall, repository, context, text, seen, item, position
        )


def _apply_retract(
    repository: SqlCompanionMemoryRepository,
    chatbot_id: ChatbotId,
    known: List[FactRecord],
    item: ExtractedFact,
) -> Optional[str]:
    """Retract the stored fact a correction names; its content."""
    from . import fact_recall

    match = _match_stored(item.content, known)
    if match is None or match.fact_id is None:
        return None
    fact_recall.retract_fact(
        repository, chatbot_id, int(match.fact_id), reason="corrected"
    )
    return match.content


def _apply_save(
    fact_recall_module,
    repository: SqlCompanionMemoryRepository,
    context: JobContext,
    text: str,
    seen: List[str],
    item: ExtractedFact,
    position: int,
) -> None:
    """Save one supported, novel candidate (or skip it)."""
    from .recall import get_bound_index

    if not is_supported(item.content, text):
        return
    if _is_duplicate(repository, context.chatbot_id, item.content, seen):
        return
    index, client = get_bound_index(int(context.chatbot_id))
    fact_recall_module.record_fact(
        repository,
        context.chatbot_id,
        item.content,
        subject=item.subject,
        source="fact-extraction",
        event_id=f"extract:{context.job_id}:{position}",
        index=index,
        client=client,
    )
    seen.append(item.content)


def _is_duplicate(
    repository: SqlCompanionMemoryRepository,
    chatbot_id: ChatbotId,
    candidate: str,
    seen: List[str],
) -> bool:
    """Two layers: B05 lookup first, algorithmic backstop always."""
    from . import fact_recall

    for hit in fact_recall.recall_facts(
        repository, chatbot_id, candidate, limit=3
    ):
        if is_same_fact(candidate, hit.content):
            return True
    return any(is_same_fact(candidate, text) for text in seen)


def _match_stored(
    content: str, known: List[FactRecord]
) -> Optional[FactRecord]:
    """The stored fact a retraction names, or None."""
    for row in known:
        if is_same_fact(content, row.content):
            return row
    return None


__all__ = [
    "ExtractFn",
    "ExtractedFact",
    "ExtractionResult",
    "build_extraction_prompt",
    "is_same_fact",
    "is_supported",
    "make_fact_extraction_handler",
    "normalize_fact_text",
    "schedule_fact_extraction",
]
