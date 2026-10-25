"""Supervisor hardening for issues #2429 and #2431.

Covers: the monitor loop tolerating transient health failures and
exiting only after N consecutive failures (F12), the signal handler
setting an event instead of raising (F14), and ensure_connected() /
the monitor noticing a requested shutdown promptly.

Hermetic: fake clients and loggers; no processes, network, or binds.
"""

from __future__ import annotations

import logging
import threading

import requests

from airunner_services.bin import airunner_headless as supervisor


class _FakeClient:
    """Double recording health_check calls with a scripted outcome."""

    def __init__(self, outcomes: list) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0
        self.base_url = "http://127.0.0.1:9999"

    def health_check(self):
        """Fail or succeed according to the scripted outcomes."""
        self.calls += 1
        if self._outcomes:
            outcome = self._outcomes.pop(0)
        else:
            outcome = None
        if isinstance(outcome, BaseException):
            raise outcome
        return {"status": "ok"}


def _logger():
    logger = logging.getLogger("test-supervisor")
    logger.setLevel(logging.CRITICAL)
    return logger


def test_transient_failures_do_not_kill_daemon() -> None:
    """Two failures then recovery keeps the monitor alive."""
    stop = threading.Event()
    client = _FakeClient(
        [
            requests.ConnectionError("spike"),
            requests.ConnectionError("gc pause"),
        ]
    )

    def _stop_after_enough() -> None:
        while client.calls < 6:
            stop.wait(timeout=1.0)
        stop.set()

    watcher = threading.Thread(target=_stop_after_enough, daemon=True)
    watcher.start()
    result = supervisor._monitor_managed_daemon(
        client,
        _logger(),
        max_consecutive_failures=3,
        poll_interval_seconds=0.01,
        stop_event=stop,
    )
    watcher.join(timeout=10)
    assert result == 0
    assert client.calls >= 6


def test_consecutive_failures_exit_with_one() -> None:
    """Three straight failures exit 1; earlier successes reset the count."""
    stop = threading.Event()
    client = _FakeClient(
        [
            requests.ConnectionError("one"),
            None,
            requests.ConnectionError("two"),
            requests.ConnectionError("three"),
            requests.ConnectionError("four"),
        ]
    )
    result = supervisor._monitor_managed_daemon(
        client,
        _logger(),
        max_consecutive_failures=3,
        poll_interval_seconds=0.01,
        stop_event=stop,
    )
    assert result == 1
    assert client.calls == 5


def test_runtime_error_failures_count_too() -> None:
    """GuiDaemonClient wraps transport errors in RuntimeError (#2429)."""
    stop = threading.Event()
    client = _FakeClient([RuntimeError("down")] * 3)
    result = supervisor._monitor_managed_daemon(
        client,
        _logger(),
        max_consecutive_failures=3,
        poll_interval_seconds=0.01,
        stop_event=stop,
    )
    assert result == 1
    assert client.calls == 3


def test_shutdown_handler_sets_event_without_raising() -> None:
    """The handler flags shutdown; it never interrupts the caller."""
    supervisor._shutdown_event.clear()
    try:
        supervisor._handle_shutdown_signal(15, None)
        supervisor._handle_shutdown_signal(2, None)
    finally:
        was_set = supervisor._shutdown_event.is_set()
        supervisor._shutdown_event.clear()
    assert was_set is True


def test_monitor_returns_zero_on_requested_shutdown() -> None:
    """A set stop event exits the loop without any health probe."""
    stop = threading.Event()
    stop.set()
    client = _FakeClient([])
    result = supervisor._monitor_managed_daemon(
        client,
        _logger(),
        poll_interval_seconds=0.01,
        stop_event=stop,
    )
    assert result == 0
    assert client.calls == 0


def _isolate_token(tmp_path, monkeypatch) -> None:
    """Point the token store at a temp path (no real config writes)."""
    from airunner_services.api import loopback_token

    monkeypatch.setattr(
        loopback_token,
        "loopback_token_path",
        lambda: tmp_path / "config" / "loopback_token",
    )
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None


def test_ensure_connected_aborts_on_stop_event(
    tmp_path, monkeypatch
) -> None:
    """A requested shutdown short-circuits the readiness wait."""
    from airunner_services.daemon_client.gui_daemon_client import (
        GuiDaemonClient,
    )

    _isolate_token(tmp_path, monkeypatch)
    stop = threading.Event()
    stop.set()
    client = GuiDaemonClient(
        config_path=tmp_path / "daemon.yaml",
        auto_start=False,
        startup_timeout_seconds=30.0,
    )
    started = threading.Event()

    class _NeverLauncher:
        def start(self) -> None:
            started.set()

    client._launcher = _NeverLauncher()  # type: ignore[assignment]
    client._healthcheck_payload = (  # type: ignore[method-assign]
        lambda **kwargs: None
    )
    assert (
        client.ensure_connected(auto_start=True, stop_event=stop)
        is False
    )
    assert started.is_set()
    assert client.last_error == "shutdown requested"


def test_wait_until_ready_unaffected_without_stop_event(
    tmp_path, monkeypatch
) -> None:
    """Without a stop event the readiness loop still succeeds."""
    from airunner_services.daemon_client.gui_daemon_client import (
        GuiDaemonClient,
    )

    _isolate_token(tmp_path, monkeypatch)
    client = GuiDaemonClient(
        config_path=tmp_path / "daemon.yaml",
        auto_start=False,
        startup_timeout_seconds=30.0,
    )
    client._healthcheck_payload = (  # type: ignore[method-assign]
        lambda **k: {"contract_version": "0.0.0"}
    )
    original = client._contract_version_mismatch_reason
    client._contract_version_mismatch_reason = (  # type: ignore[method-assign]
        lambda health: None
    )
    try:
        assert client._wait_until_ready() is True
    finally:
        client._contract_version_mismatch_reason = (  # type: ignore[method-assign]
            original
        )
