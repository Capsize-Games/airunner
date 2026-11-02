"""Serialize background RAG indexing jobs across route and worker threads."""

from __future__ import annotations

import threading
import uuid

_STATE_LOCK = threading.Lock()
_ACTIVE_TOKEN: str | None = None
_ACTIVE_CLAIMED = False
_CANCEL_REQUESTED = threading.Event()
_ACKS: dict[str, dict[str, object]] = {}
ACK_TIMEOUT_SECONDS = 5.0


def reserve_rag_index_job() -> str | None:
    """Reserve the one indexing slot before an HTTP request is accepted."""
    global _ACTIVE_TOKEN, _ACTIVE_CLAIMED
    with _STATE_LOCK:
        if _ACTIVE_TOKEN is not None:
            return None
        _ACTIVE_TOKEN = uuid.uuid4().hex
        _ACTIVE_CLAIMED = False
        _CANCEL_REQUESTED.clear()
        _ACKS[_ACTIVE_TOKEN] = {"event": threading.Event(), "accepted": None}
        return _ACTIVE_TOKEN


def claim_rag_index_job(token: str | None = None) -> str | None:
    """Claim an internal signal or validate its route-created reservation."""
    global _ACTIVE_TOKEN, _ACTIVE_CLAIMED
    with _STATE_LOCK:
        if token is not None:
            if token != _ACTIVE_TOKEN or _ACTIVE_CLAIMED:
                return None
            _ACTIVE_CLAIMED = True
            return token
        if _ACTIVE_TOKEN is not None:
            return None
        _ACTIVE_TOKEN = uuid.uuid4().hex
        _ACTIVE_CLAIMED = True
        _CANCEL_REQUESTED.clear()
        return _ACTIVE_TOKEN


def release_rag_index_job(token: str) -> None:
    """Release only the job that owns the active reservation."""
    global _ACTIVE_TOKEN, _ACTIVE_CLAIMED
    with _STATE_LOCK:
        if token == _ACTIVE_TOKEN:
            _ACTIVE_TOKEN = None
            _ACTIVE_CLAIMED = False


def owns_rag_index_job(token: str) -> bool:
    """Return whether this token still owns the active worker slot."""
    with _STATE_LOCK:
        return token == _ACTIVE_TOKEN and _ACTIVE_CLAIMED


def acknowledge_rag_index_job(token: str, accepted: bool) -> None:
    """Acknowledge that a listener actually started the reserved job."""
    with _STATE_LOCK:
        if token != _ACTIVE_TOKEN:
            return
        record = _ACKS.get(token)
        if record is None:
            return
        record["accepted"] = bool(accepted)
        event = record["event"]
        assert isinstance(event, threading.Event)
        event.set()


def get_rag_index_job_ack(token: str) -> bool | None:
    """Read the current acknowledgment without consuming its route record."""
    with _STATE_LOCK:
        record = _ACKS.get(token)
        if record is None:
            return False
        accepted = record["accepted"]
        return accepted if isinstance(accepted, bool) else None


def finish_rag_index_dispatch(token: str) -> bool:
    """Consume an acknowledgment, preserving only an acknowledged active job."""
    global _ACTIVE_TOKEN, _ACTIVE_CLAIMED
    with _STATE_LOCK:
        record = _ACKS.pop(token, None)
        accepted = bool(record and record.get("accepted") is True)
        if not accepted and token == _ACTIVE_TOKEN:
            _ACTIVE_TOKEN = None
            _ACTIVE_CLAIMED = False
        return accepted


def request_rag_index_cancel() -> bool:
    """Request cancellation for the active job without affecting later jobs."""
    with _STATE_LOCK:
        if _ACTIVE_TOKEN is None:
            return False
        _CANCEL_REQUESTED.set()
        return True


def rag_index_cancel_requested() -> bool:
    """Return whether the active job has a pending cancel request."""
    return _CANCEL_REQUESTED.is_set()
