"""Thread-safe in-memory usage ledger for Muse image jobs.

Stores only ``job_id``, ``model`` and ``image_count`` per job.
No prompt, API key, or image payload is accepted or retained.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Dict, Optional

ENV_MAX_IMAGES_PER_JOB = "AIRUNNER_MUSE_MAX_IMAGES_PER_JOB"
DEFAULT_MAX_IMAGES_PER_JOB = 8


class MuseUsageError(ValueError):
    """Raised when Muse usage input or limits are invalid."""


class MuseUsageLimitError(MuseUsageError):
    """Raised when a job would exceed the per-job image limit."""


class _CallableInt(int):
    """An ``int`` that also returns itself when called."""

    def __call__(self) -> int:
        """Return the integer value."""
        return int(self)


def _validate_text(value: str, label: str) -> str:
    """Return a stripped non-blank string or raise."""
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise MuseUsageError(f"{label} must not be blank")
    return cleaned


def _validate_image_count(value: int) -> int:
    """Return a non-negative image count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("image_count must be an integer")
    if value < 0:
        raise MuseUsageError("image_count must not be negative")
    return value


def resolve_max_images_per_job(
    max_per_job: Optional[int] = None,
) -> int:
    """Resolve the per-job limit from arg, env, or default 8."""
    if max_per_job is not None:
        if isinstance(max_per_job, bool):
            raise TypeError("max_per_job must be an integer")
        if not isinstance(max_per_job, int):
            raise TypeError("max_per_job must be an integer")
        if max_per_job < 1:
            raise MuseUsageError("max_per_job must be positive")
        return max_per_job
    raw = os.environ.get(ENV_MAX_IMAGES_PER_JOB, "").strip()
    if not raw:
        return DEFAULT_MAX_IMAGES_PER_JOB
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_MAX_IMAGES_PER_JOB
    return parsed if parsed >= 1 else DEFAULT_MAX_IMAGES_PER_JOB


def enforce_max_images_per_job(
    image_count: int, max_per_job: Optional[int] = None
) -> int:
    """Return ``image_count`` if within limit, else raise."""
    count = _validate_image_count(image_count)
    if count > resolve_max_images_per_job(max_per_job):
        raise MuseUsageLimitError("Muse image count exceeds per-job limit")
    return count


get_max_images_per_job = resolve_max_images_per_job
check_max_images_per_job = enforce_max_images_per_job
enforce_muse_image_limit = enforce_max_images_per_job


@dataclass(frozen=True)
class MuseUsageRecord:
    """Usage for one job: identifiers and counts only."""

    job_id: str
    model: str
    image_count: int

    @property
    def total_images(self) -> int:
        """Return the recorded image count."""
        return self.image_count

    total = total_images

    def __int__(self) -> int:
        """Return the recorded image count as an int."""
        return self.image_count

    def __getitem__(self, key: str) -> object:
        """Return a field by name for mapping-style access."""
        values = self.as_dict()
        if key not in values:
            raise KeyError(key)
        return values[key]

    def as_dict(self) -> Dict[str, object]:
        """Return the record as a plain dict."""
        return {
            "job_id": self.job_id,
            "model": self.model,
            "image_count": self.image_count,
        }

    to_dict = as_dict


UsageRecord = MuseUsageRecord


class MuseUsageLedger:
    """Thread-safe in-memory ledger keyed by job id."""

    def __init__(self, max_images_per_job: Optional[int] = None) -> None:
        """Create an empty ledger with an optional fixed limit."""
        if max_images_per_job is not None:
            resolve_max_images_per_job(max_images_per_job)
        self._max_images_per_job = max_images_per_job
        self._lock = threading.RLock()
        self._records: Dict[str, MuseUsageRecord] = {}

    def _limit(self, max_per_job: Optional[int]) -> int:
        """Resolve the effective limit for one operation."""
        if max_per_job is not None:
            return resolve_max_images_per_job(max_per_job)
        return resolve_max_images_per_job(self._max_images_per_job)

    def record(
        self, job_id: str, model: str, image_count: int
    ) -> MuseUsageRecord:
        """Add ``image_count`` images for ``job_id``."""
        clean_id = _validate_text(job_id, "job_id")
        clean_model = _validate_text(model, "model")
        count = _validate_image_count(image_count)
        with self._lock:
            prior = self.total_for(clean_id)
            enforce_max_images_per_job(prior + count, self._limit(None))
            record = MuseUsageRecord(clean_id, clean_model, prior + count)
            self._records[clean_id] = record
            return record

    def get(
        self,
        job_id: str,
        default: Optional[MuseUsageRecord] = None,
    ) -> Optional[MuseUsageRecord]:
        """Return the record for ``job_id`` or ``default``."""
        if not isinstance(job_id, str):
            return default
        with self._lock:
            return self._records.get(job_id.strip(), default)

    get_record = get

    @property
    def total_images(self) -> _CallableInt:
        """Return total images across jobs (also callable)."""
        with self._lock:
            total = sum(rec.image_count for rec in self._records.values())
        return _CallableInt(total)

    def total_for(self, job_id: str) -> int:
        """Return the image count recorded for one job."""
        record = self.get(job_id)
        return record.image_count if record is not None else 0

    def enforce_limit(
        self,
        job_id: str,
        image_count: int,
        max_per_job: Optional[int] = None,
    ) -> int:
        """Return prospective total or raise if over limit."""
        clean_id = _validate_text(job_id, "job_id")
        count = _validate_image_count(image_count)
        with self._lock:
            prior = self.total_for(clean_id)
            limit = self._limit(max_per_job)
        return enforce_max_images_per_job(prior + count, limit)

    check_limit = enforce_limit
    guard = enforce_limit
    enforce = enforce_limit
    enforce_max_images_per_job = enforce_limit

    def snapshot(self) -> Dict[str, MuseUsageRecord]:
        """Return a copy of all records keyed by job id."""
        with self._lock:
            return dict(self._records)

    def clear(self) -> None:
        """Remove every recorded job."""
        with self._lock:
            self._records.clear()

    reset = clear

    def __len__(self) -> int:
        """Return the number of tracked jobs."""
        with self._lock:
            return len(self._records)

    def __contains__(self, job_id: object) -> bool:
        """Return whether ``job_id`` has a record."""
        if not isinstance(job_id, str):
            return False
        with self._lock:
            return job_id.strip() in self._records

    def __repr__(self) -> str:
        """Return a content-free summary (counts only)."""
        return (
            f"MuseUsageLedger(jobs={len(self)}, "
            f"total_images={int(self.total_images)})"
        )


__all__ = [
    "DEFAULT_MAX_IMAGES_PER_JOB",
    "ENV_MAX_IMAGES_PER_JOB",
    "MuseUsageError",
    "MuseUsageLedger",
    "MuseUsageLimitError",
    "MuseUsageRecord",
    "UsageRecord",
    "check_max_images_per_job",
    "enforce_max_images_per_job",
    "enforce_muse_image_limit",
    "get_max_images_per_job",
    "resolve_max_images_per_job",
]
