"""Helpers for sharing model lifetime with embedding operations."""

from __future__ import annotations

from contextlib import nullcontext
from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def runtime_activity_locked(method: F) -> F:
    """Run one RAG operation under its owning manager's activity lock."""

    @wraps(method)
    def guarded(self: Any, *args: Any, **kwargs: Any) -> Any:
        lock = getattr(self, "runtime_activity_lock", None)
        guard = lock if lock is not None else nullcontext()
        with guard:
            return method(self, *args, **kwargs)

    return guarded  # type: ignore[return-value]
