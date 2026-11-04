"""Regression tests for the W16 desktop smoke defects (W18).

Covers: daemon signal-handler ownership across ServiceApp
construction, the ``/api/v1/catalog/bootstrap`` mount, and
conversation summaries for dataclass-shaped rows.
"""

from __future__ import annotations

import logging
import signal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from airunner_services.app.headless_runtime_mixin import (
    HeadlessRuntimeMixin,
)
from airunner_services.daemon import AIRunnerDaemon
from airunner_services.runtimes.daemon_config import DaemonConfig

Handler = Callable[[int, object], None]


def _stub_daemon(tmp_path: Path) -> AIRunnerDaemon:
    """Return a daemon whose runtime root is isolated."""
    daemon = AIRunnerDaemon(DaemonConfig(tmp_path / "daemon.yaml"))
    daemon.config.config.setdefault("runtime", {})["root"] = str(
        tmp_path / "runtime"
    )
    return daemon


def _recorder(
    handlers: dict[int, Handler],
) -> Callable[[int, Handler], None]:
    """Return a signal.signal stand-in recording handlers."""

    def _install(signum: int, handler: Handler) -> None:
        handlers[signum] = handler

    return _install


def _app_init_overwriting_handlers(
    daemon: Any,
    cleaned: list[str],
) -> Callable[[], None]:
    """Return an app-init stub mimicking ServiceApp handlers."""

    def _init() -> None:
        daemon.app = SimpleNamespace(
            cleanup=lambda: cleaned.append("app")
        )
        signal.signal(signal.SIGTERM, lambda s, f: None)
        signal.signal(signal.SIGINT, lambda s, f: None)

    return _init


def _prepare_daemon_start(
    daemon: AIRunnerDaemon,
    monkeypatch: pytest.MonkeyPatch,
    cleaned: list[str],
) -> None:
    """Stub every start() leg except handler installation."""
    monkeypatch.setattr(daemon, "_acquire_lock", lambda: True)
    init = _app_init_overwriting_handlers(daemon, cleaned)
    monkeypatch.setattr(daemon, "_init_app_or_degraded", init)
    monkeypatch.setattr(daemon, "_start_health_monitor", lambda: None)
    monkeypatch.setattr(daemon, "_start_api_server", lambda: None)
    monkeypatch.setattr(daemon, "_run_loop", lambda: None)


def test_daemon_owns_handlers_after_app_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """App construction must not steal the daemon handlers."""
    handlers: dict[int, Handler] = {}
    cleaned: list[str] = []
    monkeypatch.setattr(signal, "signal", _recorder(handlers))
    daemon = _stub_daemon(tmp_path)
    _prepare_daemon_start(daemon, monkeypatch, cleaned)
    daemon.start()
    assert handlers[signal.SIGTERM] == daemon._handle_shutdown_signal
    assert handlers[signal.SIGINT] == daemon._handle_shutdown_signal
    handlers[signal.SIGTERM](signal.SIGTERM, None)
    assert daemon.shutdown_requested is True
    daemon.shutdown()
    assert cleaned == ["app"]


class _FakeHeadlessApp(HeadlessRuntimeMixin):
    """Minimal mixin host recording cleanup-handler calls."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.logger = logging.getLogger("w18-fake-app")
        self.is_running = False

    def signal_handler(self, signum: int, frame: object) -> None:
        """Record one cleanup-handler invocation."""
        del signum, frame
        self.calls.append("app")

    def _init_headless_services(self) -> None:
        """Skip real service startup in the fake host."""


def test_headless_mixin_chains_previous_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A prior owner's handler runs before app cleanup."""
    calls: list[str] = []
    handlers: dict[int, Handler] = {}
    previous: Handler = lambda s, f: calls.append("daemon")
    monkeypatch.setattr(signal, "signal", _recorder(handlers))
    monkeypatch.setattr(signal, "getsignal", lambda n: previous)
    app = _FakeHeadlessApp(calls)
    app._init_headless_mode()
    handlers[signal.SIGTERM](signal.SIGTERM, None)
    assert calls == ["daemon", "app"]
    assert app.is_running is True


def test_catalog_bootstrap_route_is_mounted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/v1/catalog/bootstrap serves bootstrap data."""
    from fastapi.testclient import TestClient

    from airunner_services.api.server import create_app

    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    monkeypatch.delenv("AIRUNNER_API_KEY", raising=False)
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get("/api/v1/catalog/bootstrap")
    assert response.status_code == 200
    payload = response.json()
    assert "models" in payload
    assert "pipelines" in payload
    legacy = client.get("/api/v1/art/bootstrap")
    assert legacy.status_code == 200


def _conversation_data(value: Any) -> Any:
    """Build one generated ConversationData dataclass row."""
    from airunner_services.database.models.conversation import (
        Conversation,
    )

    row = Conversation.get_dataclass()()
    row.id = 7
    row.value = value
    row.summary = ""
    return row


def test_empty_dataclass_summary_is_quiet(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Empty dataclass rows summarize to '' with no warning."""
    from airunner_services.conversations import (
        conversation_history_manager as mgr_mod,
    )

    manager = mgr_mod.ConversationHistoryManager()
    with caplog.at_level(logging.WARNING):
        result = manager._conversation_summary(_conversation_data([]))
    assert result == ""
    assert "Failed to summarize" not in caplog.text
    assert "has no attribute" not in caplog.text


def _patch_summarizer(
    monkeypatch: pytest.MonkeyPatch,
    updates: list[tuple[Any, dict[str, Any]]],
) -> None:
    """Stub the ORM summarizer and summary persistence."""
    from airunner_services.database.models.conversation import (
        Conversation,
    )

    def _record_update(pk: Any = None, **kw: Any) -> bool:
        updates.append((pk, kw))
        return True

    monkeypatch.setattr(
        Conversation, "summarize", lambda self: "sentinel summary"
    )
    monkeypatch.setattr(
        Conversation.objects, "update", _record_update
    )


def test_dataclass_summary_uses_orm_summarizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-empty dataclass rows get a generated, persisted summary."""
    from airunner_services.conversations import (
        conversation_history_manager as mgr_mod,
    )

    updates: list[tuple[Any, dict[str, Any]]] = []
    _patch_summarizer(monkeypatch, updates)
    row = _conversation_data([{"name": "U", "content": "hello"}])
    manager = mgr_mod.ConversationHistoryManager()
    result = manager._conversation_summary(row)
    assert result == "sentinel summary"
    assert row.summary == "sentinel summary"
    assert updates == [(7, {"summary": "sentinel summary"})]


def test_orm_summarize_empty_conversation() -> None:
    """An ORM conversation with no messages summarizes to ''."""
    from airunner_services.database.models.conversation import (
        Conversation,
    )

    assert Conversation(value=[]).summarize() == ""
