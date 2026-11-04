"""Bounded, request-owned observation for legacy LLM callback APIs."""

from __future__ import annotations

import logging
import math
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable

from airunner_services.utils.application.signal_mediator import SignalMediator


logger = logging.getLogger(__name__)
DEFAULT_DEADLINE_SECONDS = 300.0
MAX_DEADLINE_SECONDS = 3600.0
MAX_QUEUED_EVENTS = 256
MAX_BUFFERED_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_ERROR_FRAME_BYTES = 4096


@dataclass(frozen=True)
class ObservedEvent:
    """One bounded response item held until the client consumes it."""

    payload: bytes | None = None
    text: str = ""
    turn_index: int = 0
    tools: tuple[object, ...] = ()
    terminal: bool = False
    failed: bool = False
    failure_reason: str | None = None
    replace_text: bool = False

    @property
    def size_bytes(self) -> int:
        if self.payload is not None:
            return len(self.payload)
        return len(self.text.encode("utf-8")) + sum(
            len(repr(tool).encode("utf-8")) for tool in self.tools
        )


def completion_deadline_seconds() -> float:
    """Read a finite total completion deadline, defaulting to 300 seconds."""
    raw = os.environ.get("AIRUNNER_LLM_COMPLETION_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_DEADLINE_SECONDS
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_DEADLINE_SECONDS
    if not math.isfinite(value) or not 0.1 <= value <= MAX_DEADLINE_SECONDS:
        return DEFAULT_DEADLINE_SECONDS
    return value


def cancel_owned_llm_request(app, request_id: str) -> bool:
    """Cancel only the matching active/queued local LLM worker request."""
    worker_manager = getattr(app, "_worker_manager", None)
    if worker_manager is None:
        return False
    worker = getattr(worker_manager, "_llm_generate_worker", None)
    if worker is None:
        worker = getattr(worker_manager, "llm_generate_worker", None)
    cancel = getattr(worker, "cancel_request", None)
    if not callable(cancel):
        return False
    try:
        return bool(cancel(request_id))
    except Exception:
        logger.exception("Request-owned LLM cancellation failed")
        return False


class LegacyCompletionObserver:
    """Own one request's callback state, bounded queue, deadline, and cleanup."""

    def __init__(
        self,
        request_id: str,
        error_frame: Callable[[str], bytes],
        *,
        cancel: Callable[[], object] | None = None,
        timeout_seconds: float | None = None,
        max_events: int = MAX_QUEUED_EVENTS,
        max_buffered_bytes: int = MAX_BUFFERED_BYTES,
        max_total_bytes: int = MAX_TOTAL_BYTES,
    ) -> None:
        self.request_id = request_id
        self.error_frame = error_frame
        self._cancel = cancel
        self.deadline = time.monotonic() + (
            completion_deadline_seconds()
            if timeout_seconds is None
            else timeout_seconds
        )
        self._queue: queue.Queue[ObservedEvent] = queue.Queue(
            maxsize=max_events + 1
        )
        self._max_events = max_events
        self._max_buffered_bytes = max_buffered_bytes
        self._max_total_bytes = max_total_bytes
        self._queued_events = 0
        self._buffered_bytes = 0
        self._total_bytes = 0
        self._lock = threading.RLock()
        self.done = threading.Event()
        self.last_callback_at = time.monotonic()
        self._terminal = False
        self._terminal_failure_reason: str | None = None
        self._closed = False
        self._cleaned = False
        self._cancel_on_close = False
        self._cancel_requested = False
        self._cancel_in_progress = False
        self._dispatch_finished = False
        self._dispatch_retry_attempted = False

    @property
    def active(self) -> bool:
        with self._lock:
            return not self._terminal and not self._closed

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def start_dispatch(
        self,
        sender: Callable[[Callable[[dict], None]], object],
        handler: Callable[[dict], object],
    ) -> threading.Thread:
        """Dispatch outside the caller so even kickoff uses the total deadline."""

        def kickoff() -> None:
            if not self.active:
                return
            try:
                sender(self.protected(handler))
            except Exception:
                logger.exception(
                    "Legacy LLM dispatch failed (request_id=%s)",
                    self.request_id,
                )
                self.fail("dispatch_error")
            finally:
                with self._lock:
                    self._dispatch_finished = True
                if self.closed:
                    self._unregister()
                    if self._cancel_after_terminal():
                        self._cancel_owned()

        thread = threading.Thread(target=kickoff, daemon=True)
        thread.start()
        return thread

    def protected(self, handler: Callable[[dict], object]) -> Callable[[dict], None]:
        """Wrap a route callback so late events/errors cannot strand a request."""

        def callback(data: dict) -> None:
            if not self.active:
                return
            try:
                handler(data)
            except Exception:
                logger.exception(
                    "Legacy LLM callback failed (request_id=%s)",
                    self.request_id,
                )
                self.fail("callback_error")

        return callback

    def publish(
        self,
        *,
        payload: bytes | None = None,
        text: str = "",
        turn_index: int = 0,
        tools: tuple[object, ...] | list[object] = (),
        terminal: bool = False,
        failed: bool = False,
        failure_reason: str | None = None,
        replace_text: bool = False,
    ) -> bool:
        """Queue one event; reserve one queue slot for a terminal frame."""
        event = ObservedEvent(
            payload=payload,
            text=text,
            turn_index=turn_index,
            tools=tuple(tools),
            terminal=terminal,
            failed=failed,
            failure_reason=failure_reason if failed else None,
            replace_text=replace_text,
        )
        cancel_after = False
        with self._lock:
            if self._terminal or self._closed:
                return False
            size = event.size_bytes
            if (
                not terminal
                and (
                    self._queued_events >= self._max_events
                    or self._buffered_bytes + size > self._max_buffered_bytes
                    or self._total_bytes + size > self._max_total_bytes
                )
            ):
                cancel_after = self._finish_locked("overflow", failed=True)
                accepted = False
            else:
                if terminal and self._total_bytes + size > self._max_total_bytes:
                    cancel_after = self._finish_locked("overflow", failed=True)
                    accepted = False
                else:
                    try:
                        self._queue.put_nowait(event)
                    except queue.Full:
                        cancel_after = self._finish_locked("overflow", failed=True)
                        accepted = False
                    else:
                        self._total_bytes += size
                        self._buffered_bytes += size
                        if terminal:
                            self._terminal = True
                            if failed:
                                self._terminal_failure_reason = failure_reason
                            self.done.set()
                        else:
                            self._queued_events += 1
                        self.last_callback_at = time.monotonic()
                        accepted = True
        if cancel_after:
            self._cancel_owned()
        return accepted

    def fail(self, reason: str) -> bool:
        """Queue one bounded terminal error frame and reject later callbacks."""
        with self._lock:
            should_cancel = self._finish_locked(reason, failed=True)
        if should_cancel:
            self._cancel_owned()
        return should_cancel

    def _finish_locked(self, reason: str, *, failed: bool) -> bool:
        if self._terminal or self._closed:
            return False
        payload = self.error_frame(reason)
        if len(payload) > MAX_ERROR_FRAME_BYTES:
            raise ValueError("legacy LLM terminal error frame exceeds its bound")
        event = ObservedEvent(
            payload=payload,
            terminal=True,
            failed=failed,
            failure_reason=reason if failed else None,
        )
        # Nonterminal events are capped at max_events, so this reserved slot
        # guarantees the error frame can be queued before done is signalled.
        self._queue.put_nowait(event)
        self._buffered_bytes += len(payload)
        self._terminal = True
        self._terminal_failure_reason = reason if failed else None
        self.done.set()
        return not self._cancel_requested and self._cancel is not None

    def _cancel_after_terminal(self) -> bool:
        with self._lock:
            return self._cancel_on_close or self._terminal_failure_reason in {
                "timeout", "overflow", "callback_error", "dispatch_error"
            }

    def _cancel_owned(self) -> None:
        with self._lock:
            if (
                self._cancel_requested
                or self._cancel_in_progress
                or self._cancel is None
            ):
                return
            self._cancel_in_progress = True
            cancel = self._cancel
        try:
            cancelled = bool(cancel())
        except Exception:
            logger.exception(
                "Request-owned LLM cancellation callback failed"
            )
            cancelled = False
        with self._lock:
            self._cancel_in_progress = False
            self._cancel_requested = cancelled
            retry_after_dispatch = (
                not cancelled
                and self._dispatch_finished
                and self._closed
                and self._cancel_after_terminal()
                and not self._dispatch_retry_attempted
            )
            if retry_after_dispatch:
                self._dispatch_retry_attempted = True
        if retry_after_dispatch:
            self._cancel_owned()

    def _unregister(self) -> None:
        try:
            SignalMediator().unregister_pending_request(self.request_id)
        except Exception:
            logger.exception("Could not unregister LLM observer callback")

    def next_event(self, timeout: float | None = None) -> ObservedEvent | None:
        """Return one queued event, inserting a timeout event at deadline."""
        remaining = max(0.0, self.deadline - time.monotonic())
        if remaining <= 0:
            self.fail("timeout")
            timeout = 0
        elif timeout is None:
            timeout = remaining
        else:
            timeout = min(timeout, remaining)
        try:
            event = self._queue.get(timeout=timeout)
        except queue.Empty:
            if time.monotonic() >= self.deadline:
                self.fail("timeout")
                try:
                    event = self._queue.get_nowait()
                except queue.Empty:
                    return None
            else:
                return None
        with self._lock:
            self._buffered_bytes = max(
                0, self._buffered_bytes - event.size_bytes
            )
            if not event.terminal:
                self._queued_events = max(0, self._queued_events - 1)
        return event

    def collect(self) -> list[ObservedEvent]:
        """Collect one request through its terminal event or total deadline."""
        events: list[ObservedEvent] = []
        while True:
            event = self.next_event()
            if event is None:
                continue
            events.append(event)
            if event.terminal:
                return events

    def close(self, *, cancel_if_active: bool = True) -> None:
        """Unregister this callback and cancel only unfinished owned work."""
        with self._lock:
            active = not self._terminal and not self._closed
            cancel_needed = active or self._cancel_after_terminal()
            self._closed = True
            self._cancel_on_close = self._cancel_on_close or (
                active and cancel_if_active
            )
            if active:
                self.done.set()
            if self._cleaned:
                return
            self._cleaned = True
        self._unregister()
        if cancel_if_active and cancel_needed:
            self._cancel_owned()
