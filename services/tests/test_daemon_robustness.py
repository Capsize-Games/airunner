"""Daemon robustness: file lock, shutdown path, tenant validation.

Covers the daemon hardening fixes: the exclusive lockfile replaces
the TCP-connect probe, the signal path no longer skips cleanup, and
tenant identifiers are validated before SQL interpolation.
"""

from __future__ import annotations

import signal
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from airunner_services.daemon import AIRunnerDaemon
from airunner_services.runtimes.daemon_config import DaemonConfig


def _stub_daemon(tmp_path: Path) -> AIRunnerDaemon:
    """Return a daemon whose runtime root is isolated under tmp_path."""
    daemon = AIRunnerDaemon(DaemonConfig(tmp_path / "daemon.yaml"))
    daemon.config.config.setdefault("runtime", {})["root"] = str(
        tmp_path / "runtime"
    )
    return daemon


def test_second_daemon_does_not_acquire_lock(tmp_path: Path) -> None:
    """Two daemons in one process: the second sees the lock held."""
    first = _stub_daemon(tmp_path)
    second = _stub_daemon(tmp_path)
    assert first._acquire_lock() is True
    try:
        assert second._acquire_lock() is False
        assert (tmp_path / "runtime" / "daemon-8188.lock").exists()
    finally:
        first._release_lock()
        second._release_lock()


def test_lock_released_allows_reacquire(tmp_path: Path) -> None:
    """Releasing the lock lets another daemon acquire it."""
    first = _stub_daemon(tmp_path)
    second = _stub_daemon(tmp_path)
    assert first._acquire_lock() is True
    first._release_lock()
    assert second._acquire_lock() is True
    second._release_lock()


def test_shutdown_signal_runs_cleanup(tmp_path: Path) -> None:
    """The signal handler only flags; _run_loop runs the cleanup.

    The handler must return immediately (no blocking teardown, no
    sys.exit in async-signal context); the main loop then performs
    stop/join/cleanup and exits (issues #2418, #2419).
    """
    stopped: list[str] = []
    daemon = _stub_daemon(tmp_path)
    daemon.api_server = SimpleNamespace(
        stop=lambda: stopped.append("server")
    )
    daemon.app = SimpleNamespace(cleanup=lambda: stopped.append("app"))
    daemon._handle_shutdown_signal(signal.SIGTERM, None)
    assert daemon.shutdown_requested is True
    assert daemon._signal_received == signal.SIGTERM
    assert stopped == []
    with pytest.raises(SystemExit) as excinfo:
        daemon._run_loop()
    assert excinfo.value.code == 0
    assert stopped == ["server", "app"]
    assert daemon.app is None
    assert daemon.api_server is None


def test_shutdown_is_idempotent(tmp_path: Path) -> None:
    """A second shutdown (or signal) runs cleanup exactly once."""
    calls: list[str] = []
    daemon = _stub_daemon(tmp_path)
    daemon.api_server = SimpleNamespace(
        stop=lambda: calls.append("server")
    )
    daemon.app = SimpleNamespace(cleanup=lambda: calls.append("app"))
    daemon.shutdown()
    daemon.shutdown()  # idempotent: no-op on the second call
    assert calls == ["server", "app"]


def test_rejected_tenant_identifiers() -> None:
    """Validation rejects anything outside the strict charset/cap."""
    from airunner_services.database.session import (
        _validate_tenant_identifier,
    )

    for bad in (
        "",
        "tenant-x",
        "tenant x",
        "tenant; DROP TABLE t; --",
        "tenant.x",
        '"tenant"',
        "tenänt",
        "t" * 64,
        None,
        123,
    ):
        with pytest.raises((ValueError, TypeError)):
            _validate_tenant_identifier(bad)  # type: ignore[arg-type]


def test_accepted_tenant_identifiers() -> None:
    """Normal schema names (incl. the 63-char Postgres cap) pass."""
    from airunner_services.database.session import (
        _validate_tenant_identifier,
    )

    assert _validate_tenant_identifier("default") == "default"
    assert _validate_tenant_identifier("tenant_abc123") == "tenant_abc123"
    assert _validate_tenant_identifier("A" * 63) == "A" * 63


def test_ensure_tenant_ready_rejects_bad_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No engine or SQL is touched when the identifier is invalid."""
    from airunner_services.database import session as session_mod

    monkeypatch.setenv("AIRUNNER_DB_TENANCY", "multi")
    monkeypatch.setenv(
        "AIRUNNER_DATABASE_URL", "postgresql://localhost:5432/db"
    )
    monkeypatch.delenv("AIRUNNER_MIGRATION_RUNNING", raising=False)

    def _forbid_engine(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("engine must not build for bad tenant")

    monkeypatch.setattr(
        session_mod, "create_configured_engine", _forbid_engine
    )
    with pytest.raises(ValueError):
        session_mod._ensure_tenant_ready("evil; DROP TABLE users; --")


def test_ensure_tenant_ready_migrates_once_under_threads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent first-use migrates exactly once (locked check-then-act)."""
    from airunner_services.database import session as session_mod

    monkeypatch.setenv("AIRUNNER_DB_TENANCY", "multi")
    monkeypatch.setenv(
        "AIRUNNER_DATABASE_URL", "postgresql://localhost:5432/db"
    )
    monkeypatch.delenv("AIRUNNER_MIGRATION_RUNNING", raising=False)
    monkeypatch.setattr(session_mod, "_migrated_tenants", set())

    setups: list[str] = []
    barrier = threading.Barrier(8)

    class _FakeConnection:
        def execute(self, *args: Any, **kwargs: Any) -> None:
            return None

    class _FakeTransaction:
        def __enter__(self) -> _FakeConnection:
            return _FakeConnection()

        def __exit__(self, *args: Any) -> bool:
            return False

    class _FakeEngine:
        def begin(self) -> _FakeTransaction:
            return _FakeTransaction()

    def _hammer() -> None:
        barrier.wait(timeout=30)
        session_mod._ensure_tenant_ready("tenant_race")

    monkeypatch.setattr(
        session_mod,
        "create_configured_engine",
        lambda *a, **k: _FakeEngine(),
    )
    import importlib

    setup_mod = importlib.import_module(
        "airunner_services.database.setup_database"
    )
    monkeypatch.setattr(
        setup_mod,
        "setup_database",
        lambda **k: setups.append(k.get("db_url", "")),
    )
    threads = [
        threading.Thread(target=_hammer) for _ in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not any(thread.is_alive() for thread in threads)
    assert len(setups) == 1
    assert "tenant_race" in session_mod._migrated_tenants
    session_mod._migrated_tenants.discard("tenant_race")
