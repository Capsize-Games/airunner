"""Daemon lifecycle hardening for issues #2418-#2423.

Covers: flag-only signal handlers installed at start() on the main
thread (F1/F3), SIGHUP reload performed in the loop (F4), lockfile
opened without truncation and keyed by port (F5), and bind-success
verification that fails start() fast (F2/F6).

Hermetic: no binds, no threads serving sockets, no real signals.
"""

from __future__ import annotations

import signal
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from airunner_services.api.server import APIServer
from airunner_services.daemon import AIRunnerDaemon
from airunner_services.runtimes.daemon_config import DaemonConfig


def _stub_daemon(tmp_path: Path) -> AIRunnerDaemon:
    """Return a daemon whose runtime root is isolated under tmp_path."""
    daemon = AIRunnerDaemon(DaemonConfig(tmp_path / "daemon.yaml"))
    daemon.config.config.setdefault("runtime", {})["root"] = str(
        tmp_path / "runtime"
    )
    return daemon


def test_init_installs_no_signal_handlers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Constructing a daemon has no process-global side effects."""
    installed: list[int] = []
    monkeypatch.setattr(
        signal, "signal", lambda num, h: installed.append(num)
    )
    _stub_daemon(tmp_path)
    assert installed == []


def test_start_on_worker_thread_skips_handlers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signal setup on a non-main thread warns and skips, not raises."""
    installed: list[int] = []
    monkeypatch.setattr(
        signal, "signal", lambda num, h: installed.append(num)
    )
    daemon = _stub_daemon(tmp_path)
    errors: list[BaseException] = []

    def _run_off_main_thread() -> None:
        try:
            daemon._maybe_setup_signal_handlers()
        except BaseException as exc:  # pragma: no cover - must not happen
            errors.append(exc)

    worker = threading.Thread(target=_run_off_main_thread)
    worker.start()
    worker.join(timeout=30)
    assert not worker.is_alive()
    assert errors == []
    assert installed == []


def test_setup_handlers_installs_on_main_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On the main thread start() installs SIGTERM/SIGINT/SIGHUP."""
    installed: list[int] = []
    monkeypatch.setattr(
        signal, "signal", lambda num, h: installed.append(num)
    )
    daemon = _stub_daemon(tmp_path)
    daemon._maybe_setup_signal_handlers()
    assert signal.SIGTERM in installed
    assert signal.SIGINT in installed
    assert signal.SIGHUP in installed


def test_reload_signal_only_flags(tmp_path: Path) -> None:
    """SIGHUP records the request; the config object is untouched."""
    daemon = _stub_daemon(tmp_path)
    before = daemon.config
    daemon._handle_reload_signal(signal.SIGHUP, None)
    assert daemon._reload_requested is True
    assert daemon.config is before


def test_reload_failure_keeps_active_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corrupt re-read logs and keeps serving the active config."""
    daemon = _stub_daemon(tmp_path)
    before = daemon.config
    monkeypatch.setattr(
        "airunner_services.daemon.DaemonConfig",
        lambda path: (_ for _ in ()).throw(ValueError("corrupt")),
    )
    daemon._reload_requested = True
    daemon._perform_reload()
    assert daemon.config is before


def test_reload_success_swaps_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A good re-read replaces the config object in one assignment."""
    daemon = _stub_daemon(tmp_path)
    before = daemon.config
    sentinel = SimpleNamespace(
        config_path=before.config_path, config={"server": {}}
    )
    monkeypatch.setattr(
        "airunner_services.daemon.DaemonConfig",
        lambda path: sentinel,
    )
    daemon._perform_reload()
    assert daemon.config is sentinel
    assert before is not sentinel


def test_reload_applied_from_run_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_run_loop consumes the flag once, then keeps looping."""
    daemon = _stub_daemon(tmp_path)
    daemon.shutdown_requested = False
    daemon._reload_requested = True
    performed: list[str] = []
    monkeypatch.setattr(
        daemon,
        "_perform_reload",
        lambda: performed.append("reload"),
    )
    sleeps = iter([False, True])

    def _sleep(_seconds: float) -> None:
        if next(sleeps):
            daemon.shutdown_requested = True

    monkeypatch.setattr("airunner_services.daemon.time.sleep", _sleep)
    with pytest.raises(SystemExit):
        daemon._run_loop()
    assert performed == ["reload"]
    assert daemon._reload_requested is False


def test_lock_filename_carries_port(tmp_path: Path) -> None:
    """Two configs take different locks for different ports."""
    first = _stub_daemon(tmp_path)
    assert first._lock_file_path().name == "daemon-8188.lock"
    second = _stub_daemon(tmp_path)
    second.config.config.setdefault("server", {})["port"] = 9999
    assert second._lock_file_path().name == "daemon-9999.lock"


def test_failed_acquire_preserves_holder_pid(
    tmp_path: Path,
) -> None:
    """A losing contender never truncates the holder's PID text."""
    first = _stub_daemon(tmp_path)
    second = _stub_daemon(tmp_path)
    assert first._acquire_lock() is True
    try:
        assert second._acquire_lock() is False
        content = first._lock_file_path().read_text(
            encoding="utf-8"
        )
        import os as _os

        assert content.strip() == str(_os.getpid())
    finally:
        first._release_lock()
        second._release_lock()


class _NeverBound:
    """Minimal stand-in for a uvicorn.Server that never binds."""

    started = False
    should_exit = False


def _bare_api_server() -> APIServer:
    """Return an APIServer without building the FastAPI app."""
    server = APIServer.__new__(APIServer)
    server.server = None
    server.server_thread = None
    import threading as _threading

    server._started_event = _threading.Event()
    return server


def test_wait_until_started_true_on_bind() -> None:
    """A bound server reports success and latches the event."""
    api = _bare_api_server()
    api.server = _NeverBound()
    api.server.started = True  # type: ignore[attr-defined]
    assert api.wait_until_started(timeout=1.0) is True
    assert api._started_event.is_set()


def test_wait_until_started_false_on_timeout() -> None:
    """No bind within the timeout reports failure quickly."""
    api = _bare_api_server()
    assert api.wait_until_started(timeout=0.05) is False
    assert not api._started_event.is_set()


def test_wait_until_started_false_when_thread_dies() -> None:
    """A serving thread that exits unbound fails fast, not on timeout."""
    api = _bare_api_server()
    api.server = _NeverBound()
    done = threading.Thread(target=lambda: None)
    done.start()
    done.join()
    api.server_thread = done
    assert api.wait_until_started(timeout=5.0) is False


def test_stop_before_start_is_noop(caplog: pytest.LogCaptureFixture) -> None:
    """stop() with no server (or never bound) touches nothing."""
    api = _bare_api_server()
    api.stop()
    api.server = _NeverBound()
    with caplog.at_level("WARNING"):
        api.stop()
    assert api.server is None
    assert "never finished binding" in caplog.text


def test_stop_joins_serving_thread() -> None:
    """stop() sets should_exit and joins the serving thread."""
    api = _bare_api_server()
    started = threading.Event()
    exited = threading.Event()

    class _Running:
        started = True
        should_exit = False

    running = _Running()
    api.server = running  # type: ignore[assignment]

    def _serve() -> None:
        started.set()
        while not running.should_exit:
            exited.wait(timeout=0.01)

    thread = threading.Thread(target=_serve, daemon=True)
    api.server_thread = thread
    thread.start()
    assert started.wait(timeout=5)
    api.stop(timeout=5.0)
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert running.should_exit is True
    assert api.server is None


def test_stop_warns_when_thread_lingers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A hung serving thread warns but never blocks shutdown."""
    api = _bare_api_server()

    class _Hung:
        started = True
        should_exit = False

    api.server = _Hung()  # type: ignore[assignment]
    linger = threading.Event()

    def _serve() -> None:
        linger.wait(timeout=30)

    thread = threading.Thread(target=_serve, daemon=True)
    api.server_thread = thread
    thread.start()
    with caplog.at_level("WARNING"):
        api.stop(timeout=0.05)
    assert thread.is_alive()
    assert "did not stop within" in caplog.text
    linger.set()
    thread.join(timeout=5)


class _FailingAPI:
    """APIServer double whose bind never succeeds."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        self.server_thread = threading.Thread(
            target=lambda: None, daemon=True
        )

    def start(self) -> None:
        """Pretend to serve without ever binding."""

    def wait_until_started(self, timeout: float = 15.0) -> bool:
        """Report the failed bind."""
        del timeout
        return False

    def stop(self, timeout: float = 10.0) -> None:
        """Never called on the failure path."""
        del timeout
        raise AssertionError("stop must not run without a bind")


def test_start_api_server_fails_fast_on_dead_bind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dead API fails start() instead of idling unbound in the loop."""
    daemon = _stub_daemon(tmp_path)
    monkeypatch.setattr(
        "airunner_services.daemon.APIServer", _FailingAPI
    )
    with pytest.raises(RuntimeError, match="failed to bind"):
        daemon._start_api_server()
