"""Shared daemon-visible status for one active RAG indexing task."""

from __future__ import annotations

import threading
import time
from typing import Any


class RAGIndexStatusTracker:
    """Track the latest document-indexing state for daemon polling."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = self._initial_state()

    @staticmethod
    def _initial_state() -> dict[str, Any]:
        """Return the default idle tracker state."""
        return {
            "active": False,
            "current": 0,
            "total": 0,
            "progress": 0,
            "document_name": "",
            "message": "",
            "success": None,
            "updated_at": 0.0,
        }

    def start(self, *, total: int = 0, message: str = "") -> None:
        """Mark one indexing task as active."""
        with self._lock:
            self._state = {
                **self._initial_state(),
                "active": True,
                "total": max(int(total or 0), 0),
                "message": message,
                "updated_at": time.monotonic(),
            }

    def progress(self, data: dict[str, Any]) -> None:
        """Store one in-flight indexing progress update."""
        current = max(int(data.get("current", 0) or 0), 0)
        total = max(int(data.get("total", 0) or 0), 0)
        progress = int(data.get("progress", 0) or 0)
        if total > 0:
            progress = max(0, min(progress, 100))
        else:
            progress = max(progress, 0)

        document_name = str(
            data.get("document_name") or data.get("documentName") or ""
        ).strip()

        with self._lock:
            self._state.update(
                {
                    "active": True,
                    "current": current,
                    "total": total,
                    "progress": progress,
                    "document_name": document_name,
                    "updated_at": time.monotonic(),
                }
            )

    def complete(self, data: dict[str, Any]) -> None:
        """Store one terminal indexing result."""
        success = bool(data.get("success", False))
        message = str(data.get("message", "") or "").strip()
        with self._lock:
            progress = 100 if success else int(self._state.get("progress", 0))
            self._state.update(
                {
                    "active": False,
                    "progress": max(0, min(progress, 100)),
                    "message": message,
                    "success": success,
                    "updated_at": time.monotonic(),
                }
            )

    def cancel_requested(self) -> None:
        """Record that cancellation was requested for the active task."""
        with self._lock:
            if not self._state.get("active", False):
                return
            self._state["message"] = "Cancelling indexing..."
            self._state["updated_at"] = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        """Return one copy of the current tracker state."""
        with self._lock:
            return dict(self._state)


rag_index_status_tracker = RAGIndexStatusTracker()


__all__ = ["RAGIndexStatusTracker", "rag_index_status_tracker"]
