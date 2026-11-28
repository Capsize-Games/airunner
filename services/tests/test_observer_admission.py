"""Unit tests for LegacyCompletionObserver._admit_event_locked.

The admission logic was extracted to keep publish() within the
long-function threshold. These tests pin each admission branch:
accept, terminal accept, event-count overflow, terminal overflow.
"""

from airunner_services.api.routes.legacy_llm_observer import (
    LegacyCompletionObserver,
    ObservedEvent,
)


def _observer(**kwargs):
    return LegacyCompletionObserver(
        "request-a", lambda reason: f"error:{reason}".encode(), **kwargs
    )


def _event(text="abc"):
    return ObservedEvent(payload=None, text=text, turn_index=0)


def test_accept_non_terminal():
    observer = _observer(timeout_seconds=1)
    accepted, cancel = observer._admit_event_locked(
        _event(), False, False, None
    )
    assert (accepted, cancel) == (True, False)
    assert observer._queued_events == 1
    assert observer._buffered_bytes == len(b"abc")


def test_terminal_accept_sets_done():
    observer = _observer(timeout_seconds=1)
    accepted, cancel = observer._admit_event_locked(
        _event(), True, False, None
    )
    assert (accepted, cancel) == (True, False)
    assert observer.done.is_set()
    assert observer._terminal is True


def test_terminal_failure_records_reason():
    observer = _observer(timeout_seconds=1)
    observer._admit_event_locked(_event(), True, True, "boom")
    assert observer._terminal_failure_reason == "boom"


def test_non_terminal_count_overflow_requests_cancel():
    observer = _observer(
        timeout_seconds=1, max_events=1, cancel=lambda: None
    )
    observer.publish(text="first")
    accepted, cancel = observer._admit_event_locked(
        _event("x"), False, False, None
    )
    assert accepted is False
    assert cancel is True


def test_terminal_overflow_requests_cancel():
    observer = _observer(
        timeout_seconds=1, max_total_bytes=4, cancel=lambda: None
    )
    observer.publish(text="1234")
    accepted, cancel = observer._admit_event_locked(
        _event("x"), True, False, None
    )
    assert accepted is False
    assert cancel is True


def test_overflow_without_cancel_callable_reports_no_cancel():
    observer = _observer(
        timeout_seconds=1, max_total_bytes=4
    )
    observer.publish(text="1234")
    accepted, cancel = observer._admit_event_locked(
        _event("x"), True, False, None
    )
    assert accepted is False
    assert cancel is False


def test_publish_rejected_after_terminal():
    observer = _observer(timeout_seconds=1)
    assert observer.publish(text="done", terminal=True)
    assert not observer.publish(text="late")


def test_publish_rejected_after_close():
    observer = _observer(timeout_seconds=1)
    observer.fail("manual")
    assert not observer.publish(text="late")
