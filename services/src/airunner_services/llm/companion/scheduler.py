"""Bounded background-job scheduler contract for companion work (B01).

An interface only — B06 implements this as Desktop's durable, bounded
job mechanism (with idempotency keys and bounded concurrency per the
parent spec's architecture decision #4); B08/B09/B15 schedule through
it rather than spawning their own threads/timers.

Frozen upstream shape this maps to (W01 §2, §3): every background
cognition task found (mood, rolling compression, episodic summary,
curiosity, interjections) is already a plain ``asyncio.create_task``
fire-and-forget call keyed off session-rotation, not a Celery job —
this contract keeps that same "fire against one session, run once,
bounded" shape rather than introducing a heavier task-queue concept
Desktop does not otherwise have. It differs from upstream in one
required way the parent spec calls out explicitly: GPU-dependent
background work here must arbitrate for the model resource the same
way interactive generation does (architecture decision #4) — no
background job may load its own independent model instance.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from .contracts import ChatbotId, SessionId


class CompanionJobType(str, Enum):
    """Kinds of bounded background job a companion turn may schedule.

    One member per background capability confirmed in W01 §3 (upstream
    module cited per member); additive only.
    """

    # upstream: llm/intra_session_mood.py, llm/mood/*
    MOOD_UPDATE = "mood_update"
    # upstream: llm/rolling_compressor.py
    ROLLING_COMPRESSION = "rolling_compression"
    # upstream: llm/episodic_summarizer.py
    EPISODIC_SUMMARY = "episodic_summary"
    # upstream: llm/memory_updater.py (cascades after EPISODIC_SUMMARY
    # upstream too — see W01 §3's "MEMORY_UPDATER... Cascaded from
    # EPISODIC_SUMMARIZER" note; a B06 scheduler may model this as one
    # job enqueuing the next, or as a single combined job — B08/B09's
    # call, not fixed here)
    MEMORY_BLEND = "memory_blend"
    # upstream: llm/knowledge_extractor.py
    FACT_EXTRACTION = "fact_extraction"
    # upstream: llm/curiosity_engine.py
    CURIOSITY = "curiosity"


class CompanionJobRequest(BaseModel):
    """One request to schedule bounded background companion work."""

    model_config = ConfigDict(extra="forbid")

    job_type: CompanionJobType
    chatbot_id: ChatbotId
    session_id: Optional[SessionId] = None
    # Required, caller-generated: the same (job_type, chatbot_id,
    # session_id, idempotency_key) must never execute twice, per the
    # parent spec's "persist background jobs with idempotency keys"
    # requirement. Session-rotation-triggered jobs would typically key
    # this off the session's rotation boundary (e.g. its closing turn
    # id) so a retry after a crash cannot double-run the same job.
    idempotency_key: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class CompanionJobHandle(BaseModel):
    """Returned immediately on schedule; the job itself runs later."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    job_type: CompanionJobType
    accepted: bool
    reason: Optional[str] = None  # set when accepted=False (e.g. duplicate)


@runtime_checkable
class CompanionScheduler(Protocol):
    """Schedules bounded, idempotent background companion jobs."""

    def schedule(self, request: CompanionJobRequest) -> CompanionJobHandle:
        """Enqueue one job; must be safe to call more than once with the
        same idempotency key (the second call is a no-op, not an error)."""
        ...


__all__ = [
    "CompanionJobHandle",
    "CompanionJobRequest",
    "CompanionJobType",
    "CompanionScheduler",
]
