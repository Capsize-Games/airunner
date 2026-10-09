"""Service-owned companion background-job model (release issue B06)."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from airunner_services.database.base import BaseModel


class CompanionJob(BaseModel):
    """One durable, idempotent background companion job.

    The unique constraint on ``(chatbot_id, job_type,
    idempotency_key)`` is what makes enqueue idempotent: the caller
    generates the key (rotation-triggered jobs fold the session's
    rotation boundary into it, per ``scheduler.py``), so a duplicate
    enqueue or a retry after a crash can never insert a second row
    for the same logical job. ``session_id`` is deliberately *not*
    part of the key: it is nullable (not every job is scoped to one
    session) and SQLite treats NULLs as distinct in unique
    constraints, so including it would silently defeat dedup for
    session-less jobs.

    ``status`` is one of ``queued``/``leased``/``succeeded``/``failed``/
    ``cancelled`` (see ``llm/companion/jobs.py``). ``attempts`` counts
    claims, incremented atomically at claim time; a job whose lease
    expires is requeued until ``attempts`` reaches ``max_attempts``,
    then marked ``failed`` -- capped retries with no unbounded loop.
    """

    __tablename__ = "companion_jobs"
    __table_args__ = (
        UniqueConstraint(
            "chatbot_id",
            "job_type",
            "idempotency_key",
            name="uq_companion_jobs_chatbot_type_key",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(
        Integer, ForeignKey("chatbots.id"), nullable=False, index=True
    )
    session_id = Column(
        Integer,
        ForeignKey("companion_sessions.id"),
        nullable=True,
        index=True,
    )
    job_type = Column(String, nullable=False, index=True)
    idempotency_key = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String, nullable=False, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    lease_owner = Column(String, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    run_after = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_error = Column(Text, nullable=True)


__all__ = ["CompanionJob"]
