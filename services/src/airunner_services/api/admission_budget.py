"""Bound active work and request starts for an authenticated route group."""

from collections import deque
from threading import Lock
from time import monotonic


class AdmissionBudget:
    """Keep a bounded rolling window and active count without waiting."""

    def __init__(self, capacity: int, per_minute: int) -> None:
        self.capacity = capacity
        self.per_minute = per_minute
        self._active = 0
        self._starts: deque[float] = deque()
        self._lock = Lock()

    def acquire(self) -> bool:
        """Admit work only when both limits permit another request."""
        now = monotonic()
        with self._lock:
            while self._starts and self._starts[0] <= now - 60:
                self._starts.popleft()
            if self._active >= self.capacity:
                return False
            if len(self._starts) >= self.per_minute:
                return False
            self._active += 1
            self._starts.append(now)
            return True

    def release(self) -> None:
        """Release the active slot after the complete response lifecycle."""
        with self._lock:
            self._active -= 1
