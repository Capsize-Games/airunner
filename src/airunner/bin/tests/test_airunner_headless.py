"""Focused tests for the daemon-backed airunner-headless CLI."""

from pathlib import Path
from types import SimpleNamespace

import yaml

import airunner.bin.airunner_headless as headless_module


class FakeLogger:
    """Minimal logger double for CLI tests."""

    def __init__(self):
        self.messages = []

    def info(self, message, *args, **kwargs):
        self.messages.append(("info", message, args))

    def error(self, message, *args, **kwargs):
        self.messages.append(("error", message, args))


class FakeClient:
    """Minimal daemon client double for CLI tests."""

    def __init__(self, *, existing: bool, launchable: bool = True):
        self.existing = existing
        self.launchable = launchable
        self.last_error = "daemon unavailable"
        self.base_url = "http://127.0.0.1:8080"
        self.calls = []
        self.stop_process = []

    def ensure_connected(self, *, auto_start=None):
        self.calls.append(auto_start)
        if auto_start is False:
            return self.existing
        return self.launchable

    def health_check(self):
        return {"status": "ready"}

    def disconnect(self, *, stop_process=False):
        self.stop_process.append(stop_process)


def test_connect_only_reuses_existing_daemon(monkeypatch, tmp_path):
    logger = FakeLogger()
    client = FakeClient(existing=True)
    prepared = []

    monkeypatch.setattr(headless_module, "_print_banner", lambda: None)
    monkeypatch.setattr(
        headless_module,
        "_configure_logging",
        lambda: (logger, 20),
    )
    monkeypatch.setattr(
        headless_module,
        "_register_shutdown_handlers",
        lambda: None,
    )
    monkeypatch.setattr(
        headless_module,
        "_prepare_daemon_config",
        lambda args, port: tmp_path / "session.yaml",
    )
    monkeypatch.setattr(
        headless_module,
        "_build_daemon_client",
        lambda path: client,
    )
    monkeypatch.setattr(
        headless_module,
        "_prepare_managed_daemon_launch",
        lambda: prepared.append(True),
    )

    result = headless_module.main(["--connect-only"])

    assert result == 0
    assert client.calls == [False]
    assert prepared == []


def test_launches_managed_daemon_when_missing(monkeypatch, tmp_path):
    logger = FakeLogger()
    client = FakeClient(existing=False, launchable=True)
    prepared = []
    monitored = []

    monkeypatch.setattr(headless_module, "_print_banner", lambda: None)
    monkeypatch.setattr(
        headless_module,
        "_configure_logging",
        lambda: (logger, 20),
    )
    monkeypatch.setattr(
        headless_module,
        "_register_shutdown_handlers",
        lambda: None,
    )
    monkeypatch.setattr(
        headless_module,
        "_prepare_daemon_config",
        lambda args, port: tmp_path / "session.yaml",
    )
    monkeypatch.setattr(
        headless_module,
        "_build_daemon_client",
        lambda path: client,
    )
    monkeypatch.setattr(
        headless_module,
        "_prepare_managed_daemon_launch",
        lambda: prepared.append(True),
    )
    monkeypatch.setattr(
        headless_module,
        "_monitor_managed_daemon",
        lambda daemon_client, logger_obj: monitored.append(True) or 0,
    )

    result = headless_module.main([])

    assert result == 0
    assert client.calls == [False, True]
    assert prepared == [True]
    assert monitored == [True]
    assert client.stop_process == [True]


def test_connect_only_fails_when_daemon_missing(monkeypatch, tmp_path):
    logger = FakeLogger()
    client = FakeClient(existing=False, launchable=False)

    monkeypatch.setattr(headless_module, "_print_banner", lambda: None)
    monkeypatch.setattr(
        headless_module,
        "_configure_logging",
        lambda: (logger, 20),
    )
    monkeypatch.setattr(
        headless_module,
        "_register_shutdown_handlers",
        lambda: None,
    )
    monkeypatch.setattr(
        headless_module,
        "_prepare_daemon_config",
        lambda args, port: tmp_path / "session.yaml",
    )
    monkeypatch.setattr(
        headless_module,
        "_build_daemon_client",
        lambda path: client,
    )

    result = headless_module.main(["--connect-only"])

    assert result == 1
    assert client.calls == [False]


def test_prepare_daemon_config_overrides_server_only(monkeypatch, tmp_path):
    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path))
    base_config = tmp_path / "daemon.yaml"
    base_config.write_text(
        yaml.safe_dump(
            {
                "server": {
                    "host": "127.0.0.1",
                    "port": 8188,
                    "enable_cors": True,
                    "allowed_origins": ["http://localhost:*"],
                },
                "logging": {"level": "INFO", "file": "daemon.log"},
            }
        ),
        encoding="utf-8",
    )
    args = SimpleNamespace(host="0.0.0.0", daemon_config=base_config)

    session_config = headless_module._prepare_daemon_config(args, 9000)

    try:
        config = yaml.safe_load(session_config.read_text(encoding="utf-8"))
    finally:
        session_config.unlink(missing_ok=True)

    assert session_config.parent.name == "configs"
    assert config["server"]["host"] == "0.0.0.0"
    assert config["server"]["port"] == 9000
    assert config["server"]["enable_cors"] is True
    assert config["server"]["allowed_origins"] == ["http://localhost:*"]