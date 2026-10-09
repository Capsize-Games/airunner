"""Durable, bounded background-job scheduler (release issue B06).

Implements the B01 ``CompanionScheduler`` contract against Desktop's
own SQLAlchemy/SQLite database: persisted job records, idempotency
keys, a bounded queue, leases with capped retries, and restart
recovery. No Celery, no Redis -- one table (``companion_jobs``) plus
this module.

Deliberately **not** re-exported from this package's ``__init__``:
like ``repository.py``, this submodule imports SQLAlchemy, which the
package-level import must stay free of (see
``services/tests/test_release_b01.py``). Import it directly.

GPU arbitration: this module performs no model, network, or GPU I/O
itself and imports no runtime or model-management module. A handler
whose work needs inference receives the caller-injected ``arbitrate``
callable on its ``JobContext`` and must request GPU work through it
(the daemon wires it to the existing runtime registry, the same
arbitration interactive generation uses) rather than loading any
model instance of its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.companion_job import CompanionJob
from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.session import session_scope

from .contracts import ChatbotId, SessionId
from .scheduler import (
    CompanionJobHandle,
    CompanionJobRequest,
    CompanionJobType,
)

# Stored ``CompanionJob.status`` values. Terminal: succeeded, failed,
# cancelled. A leased row whose ``lease_expires_at`` has passed is
# dead (its worker crashed) and is requeued by recovery, never run
# twice concurrently while the lease is live.
JOB_QUEUED = "queued"
JOB_LEASED = "leased"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"
JOB_CANCELLED = "cancelled"


@dataclass(frozen=True)
class JobContext:
    """What a handler observes about the one job it is running."""

    job_id: str
    job_type: CompanionJobType
    chatbot_id: ChatbotId
    session_id: Optional[SessionId]
    payload: Dict[str, Any] = field(default_factory=dict)
    # 1-based: 1 on the first claim, incremented on every reclaim.
    attempt: int = 1
    # Injected runtime-arbitration entry point (or None when the
    # scheduler was built without one). The only GPU path a handler
    # may use -- see the module docstring.
    arbitrate: Optional[Callable[..., Any]] = None


class JobOutcome(BaseModel):
    """What one ``run_due`` call did with one job it executed."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    # The stored job_type string (not the enum: an outcome must still
    # be reportable when the stored value itself is unknown).
    job_type: str
    # The job's status after this call (succeeded, failed, or queued
    # again for a retry -- never leased: this worker no longer holds
    # it either way).
    status: str
    attempts: int
    error: Optional[str] = None


# A handler runs one claimed job to completion (or raises). It must be
# idempotent: a crash between the handler's side effect and the
# completion write means recovery will run it again for the same
# idempotency key, and at-least-once is the strongest guarantee any
# lease system can offer.
JobHandler = Callable[[JobContext], None]

# Runs a thunk synchronously. The default runs it inline; production
# passes a thread-pool submitter that blocks until done. Must raise
# the thunk's exception to the caller -- a fire-and-forget executor
# cannot report completion and must not be used here.
ExecutorFn = Callable[[Callable[[], None]], None]


def _inline_executor(thunk: Callable[[], None]) -> None:
    thunk()


class DurableCompanionScheduler:
    """``CompanionScheduler`` backed by persisted ``companion_jobs``."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = datetime.utcnow,
        executor: ExecutorFn = _inline_executor,
        arbitrate: Optional[Callable[..., Any]] = None,
        handlers: Optional[Dict[CompanionJobType, JobHandler]] = None,
        max_pending_per_chatbot: int = 64,
        max_concurrent: int = 2,
        lease_duration: timedelta = timedelta(minutes=5),
        max_attempts: int = 3,
        retry_backoff: timedelta = timedelta(seconds=30),
    ) -> None:
        self._clock = clock
        self._executor = executor
        self._arbitrate = arbitrate
        self._handlers: Dict[CompanionJobType, JobHandler] = dict(
            handlers or {}
        )
        self._max_pending = max_pending_per_chatbot
        self._max_concurrent = max_concurrent
        self._lease_duration = lease_duration
        self._max_attempts = max_attempts
        self._retry_backoff = retry_backoff

    def register_handler(
        self, job_type: CompanionJobType, handler: JobHandler
    ) -> None:
        """Run ``handler`` for every claimed job of ``job_type``.

        Last registration wins. A claimed job with no registered
        handler is marked failed (with ``last_error`` set), never
        retried and never run -- a missing handler is a wiring bug,
        not a transient fault.
        """
        self._handlers[job_type] = handler

    def schedule(self, request: CompanionJobRequest) -> CompanionJobHandle:
        """Persist one job; a repeated key is a no-op, not an error."""
        now = self._clock()
        with session_scope() as db:
            existing = _find_by_key(db, request)
            if existing is not None:
                return CompanionJobHandle(
                    job_id=str(existing.id),
                    job_type=request.job_type,
                    accepted=False,
                    reason="duplicate",
                )
            _require_owner(db, request)
            pending = _pending_count(db, int(request.chatbot_id))
            if pending >= self._max_pending:
                return CompanionJobHandle(
                    job_id="",
                    job_type=request.job_type,
                    accepted=False,
                    reason="queue_full",
                )
            row = CompanionJob(
                chatbot_id=int(request.chatbot_id),
                session_id=(
                    None
                    if request.session_id is None
                    else int(request.session_id)
                ),
                job_type=request.job_type.value,
                idempotency_key=request.idempotency_key,
                payload=dict(request.payload),
                status=JOB_QUEUED,
                attempts=0,
                max_attempts=self._max_attempts,
                run_after=now,
                created_at=now,
                updated_at=now,
            )
            # A concurrent duplicate enqueue can pass the lookup above
            # before either transaction commits; the unique
            # (chatbot_id, job_type, idempotency_key) constraint is
            # the backstop, mirroring repository.py's savepoint
            # retry. Ownership was validated above, so the only
            # remaining integrity failure is that key.
            savepoint = db.begin_nested()
            db.add(row)
            try:
                db.flush()
            except IntegrityError:
                savepoint.rollback()
                winner = _find_by_key(db, request)
                if winner is None:  # pragma: no cover - defensive
                    raise
                return CompanionJobHandle(
                    job_id=str(winner.id),
                    job_type=request.job_type,
                    accepted=False,
                    reason="duplicate",
                )
            # A concurrent enqueue can also pass the pre-check above
            # in the same window; re-check after our own insert so the
            # committed state never exceeds the bound, withdrawing our
            # own row (not another writer's) when we lost that race.
            pending_after = _pending_count(db, int(request.chatbot_id))
            if pending_after > self._max_pending:
                db.delete(row)
                db.flush()
                return CompanionJobHandle(
                    job_id="",
                    job_type=request.job_type,
                    accepted=False,
                    reason="queue_full",
                )
            return CompanionJobHandle(
                job_id=str(row.id),
                job_type=request.job_type,
                accepted=True,
            )

    def cancel(self, job_id: str) -> bool:
        """Cancel one queued job; True only when it was queued.

        Deterministic: terminal jobs, leased jobs, unknown ids, and
        malformed ids all return False rather than raising. A leased
        job is owned by a live worker until its lease expires, so it
        cannot be cancelled out from under that worker.
        """
        try:
            primary_key = int(job_id)
        except (TypeError, ValueError):
            return False
        with session_scope() as db:
            row = (
                db.query(CompanionJob)
                .filter(CompanionJob.id == primary_key)
                .one_or_none()
            )
            if row is None or row.status != JOB_QUEUED:
                return False
            row.status = JOB_CANCELLED
            row.updated_at = self._clock()
            return True

    def recover_expired_leases(self) -> int:
        """Requeue jobs whose lease expired (their worker is dead).

        Any worker may recover any expired lease -- that is the whole
        point after a restart, when the previous owner no longer
        exists. A job already at its attempt cap is marked failed
        instead of being requeued. Returns the recovered count.
        """
        now = self._clock()
        recovered = 0
        with session_scope() as db:
            stale = (
                db.query(CompanionJob)
                .filter(
                    CompanionJob.status == JOB_LEASED,
                    CompanionJob.lease_expires_at <= now,
                )
                .order_by(CompanionJob.id)
                .all()
            )
            for row in stale:
                if row.attempts >= row.max_attempts:
                    row.status = JOB_FAILED
                    row.last_error = "lease expired; retry budget exhausted"
                else:
                    row.status = JOB_QUEUED
                    row.run_after = now
                row.lease_owner = None
                row.lease_expires_at = None
                row.updated_at = now
                recovered += 1
        return recovered

    def run_due(self, owner: str, *, limit: int = 1) -> List[JobOutcome]:
        """Claim and execute due jobs; restarts recover first.

        Recovery runs before claiming, so a restarted process picks
        up both queued jobs and crashed leases on its first pump with
        no separate recovery step. At most ``limit`` jobs are claimed,
        and never more than ``max_concurrent`` live leases exist
        afterwards. Each claimed job runs through the injected
        executor; the handler executes outside any open session, so a
        handler that uses the database itself never shares this
        worker's transaction.
        """
        if limit <= 0:
            return []
        self.recover_expired_leases()
        claimed = self._claim_due(owner, limit)
        return [self._execute(owner, job_id) for job_id in claimed]

    def _claim_due(self, owner: str, limit: int) -> List[int]:
        now = self._clock()
        with session_scope() as db:
            live = (
                db.query(func.count(CompanionJob.id))
                .filter(
                    CompanionJob.status == JOB_LEASED,
                    CompanionJob.lease_expires_at > now,
                )
                .scalar()
                or 0
            )
            budget = min(limit, self._max_concurrent - live)
            if budget <= 0:
                return []
            candidates = (
                db.query(CompanionJob.id)
                .filter(
                    CompanionJob.status == JOB_QUEUED,
                    CompanionJob.run_after <= now,
                )
                .order_by(CompanionJob.run_after, CompanionJob.id)
                .limit(budget)
                .all()
            )
            claimed: List[int] = []
            for (candidate_id,) in candidates:
                # Conditional UPDATE, not read-then-write: two workers
                # racing for the same row are serialized by the write
                # itself (SQLite ignores SELECT ... FOR UPDATE), and
                # exactly one sees rowcount 1.
                result = db.execute(
                    update(CompanionJob)
                    .where(
                        CompanionJob.id == candidate_id,
                        CompanionJob.status == JOB_QUEUED,
                    )
                    .values(
                        status=JOB_LEASED,
                        lease_owner=owner,
                        lease_expires_at=now + self._lease_duration,
                        attempts=CompanionJob.attempts + 1,
                        updated_at=now,
                    )
                )
                if result.rowcount == 1:
                    claimed.append(candidate_id)
            return claimed

    def _execute(self, owner: str, job_id: int) -> JobOutcome:
        with session_scope() as db:
            row = (
                db.query(CompanionJob).filter(CompanionJob.id == job_id).one()
            )
            snapshot = _ClaimSnapshot(
                job_id=row.id,
                raw_job_type=row.job_type,
                chatbot_id=row.chatbot_id,
                session_id=row.session_id,
                payload=dict(row.payload or {}),
                attempts=row.attempts,
                max_attempts=row.max_attempts,
            )
        try:
            job_type = CompanionJobType(snapshot.raw_job_type)
        except ValueError:
            return self._complete(
                owner,
                snapshot,
                JOB_FAILED,
                f"unknown job type {snapshot.raw_job_type!r}",
            )
        handler = self._handlers.get(job_type)
        if handler is None:
            return self._complete(
                owner,
                snapshot,
                JOB_FAILED,
                f"no handler registered for {job_type.value}",
            )
        context = JobContext(
            job_id=str(snapshot.job_id),
            job_type=job_type,
            chatbot_id=ChatbotId(snapshot.chatbot_id),
            session_id=(
                None
                if snapshot.session_id is None
                else SessionId(snapshot.session_id)
            ),
            payload=dict(snapshot.payload),
            attempt=snapshot.attempts,
            arbitrate=self._arbitrate,
        )
        try:
            self._executor(lambda: handler(context))
        except Exception as exc:
            # Recorded on the row (truncated by the TEXT column, never
            # re-raised): one failing job must not kill the pump, and
            # the attempt cap bounds how often it can recur.
            if snapshot.attempts >= snapshot.max_attempts:
                return self._complete(owner, snapshot, JOB_FAILED, str(exc))
            return self._complete(owner, snapshot, JOB_QUEUED, str(exc))
        return self._complete(owner, snapshot, JOB_SUCCEEDED, None)

    def _complete(
        self,
        owner: str,
        snapshot: _ClaimSnapshot,
        status: str,
        error: Optional[str],
    ) -> JobOutcome:
        now = self._clock()
        if status == JOB_QUEUED:
            # Retry, not success: linear backoff from the attempt that
            # just failed, still capped by max_attempts at claim and
            # recovery time.
            run_after = now + self._retry_backoff * snapshot.attempts
        else:
            run_after = None
        with session_scope() as db:
            # Fenced by owner: if the lease expired mid-execution and
            # another worker already recovered this row, rowcount is 0
            # and this worker must not overwrite that decision.
            values: Dict[str, Any] = {
                "status": status,
                "lease_owner": None,
                "lease_expires_at": None,
                "last_error": error,
                "updated_at": now,
            }
            if run_after is not None:
                values["run_after"] = run_after
            result = db.execute(
                update(CompanionJob)
                .where(
                    CompanionJob.id == snapshot.job_id,
                    CompanionJob.status == JOB_LEASED,
                    CompanionJob.lease_owner == owner,
                )
                .values(**values)
            )
            if result.rowcount == 1:
                attempts = snapshot.attempts
            else:
                current = (
                    db.query(CompanionJob)
                    .filter(CompanionJob.id == snapshot.job_id)
                    .one()
                )
                status = current.status
                attempts = current.attempts
                error = f"lease lost during execution; job is {status}"
        return JobOutcome(
            job_id=str(snapshot.job_id),
            job_type=snapshot.raw_job_type,
            status=status,
            attempts=attempts,
            error=error,
        )


@dataclass(frozen=True)
class _ClaimSnapshot:
    """The claimed row's execution inputs, read before the handler runs.

    The handler executes outside any open session (it may use the
    database itself), so completion works from this snapshot plus a
    fenced conditional UPDATE rather than a held ORM instance.
    """

    job_id: int
    raw_job_type: str
    chatbot_id: int
    session_id: Optional[int]
    payload: Dict[str, Any]
    attempts: int
    max_attempts: int


def _find_by_key(db, request: CompanionJobRequest) -> Optional[CompanionJob]:
    """Return the row already stored for this idempotency key, if any."""
    return (
        db.query(CompanionJob)
        .filter(
            CompanionJob.chatbot_id == int(request.chatbot_id),
            CompanionJob.job_type == request.job_type.value,
            CompanionJob.idempotency_key == request.idempotency_key,
        )
        .one_or_none()
    )


def _pending_count(db, chatbot_id: int) -> int:
    """Queued plus leased rows for one chatbot (the bounded backlog)."""
    return (
        db.query(func.count(CompanionJob.id))
        .filter(
            CompanionJob.chatbot_id == chatbot_id,
            CompanionJob.status.in_([JOB_QUEUED, JOB_LEASED]),
        )
        .scalar()
        or 0
    )


def _require_owner(db, request: CompanionJobRequest) -> None:
    """Reject jobs naming a chatbot (or session) that does not exist.

    Raises ValueError like repository.py's missing-session check, so a
    flush-time IntegrityError below can only mean the idempotency-key
    race with a concurrent duplicate enqueue -- never a dangling
    foreign key misreported as a duplicate.
    """
    chatbot = (
        db.query(Chatbot)
        .filter(Chatbot.id == int(request.chatbot_id))
        .one_or_none()
    )
    if chatbot is None:
        raise ValueError(f"No chatbot {request.chatbot_id}")
    if request.session_id is not None:
        session_row = (
            db.query(CompanionSession)
            .filter(
                CompanionSession.id == int(request.session_id),
                CompanionSession.chatbot_id == int(request.chatbot_id),
            )
            .one_or_none()
        )
        if session_row is None:
            raise ValueError(
                f"No session {request.session_id} for chatbot "
                f"{request.chatbot_id}"
            )


__all__ = [
    "JOB_CANCELLED",
    "JOB_FAILED",
    "JOB_LEASED",
    "JOB_QUEUED",
    "JOB_SUCCEEDED",
    "DurableCompanionScheduler",
    "ExecutorFn",
    "JobContext",
    "JobHandler",
    "JobOutcome",
]
