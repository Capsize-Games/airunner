"""Tests for daemon lifecycle ownership."""

from pathlib import Path
from types import SimpleNamespace


def _daemon_config():
    return SimpleNamespace(
        config={"logging": {}, "models": {}, "health": {}, "server": {}},
        config_path=Path("/tmp/daemon.yaml"),
    )


def test_daemon_owns_headless_lifecycle(monkeypatch):
    import airunner.services.daemon as daemon_module

    calls = []

    class FakeLifecycleService:
        def initialize(self):
            calls.append("initialize")

        def preload_llm_model(self):
            calls.append("preload")

    class FakeApp:
        def __init__(self, **kwargs):
            calls.append(("app", kwargs))
            self.lifecycle_service = FakeLifecycleService()

        def ensure_lifecycle_service(self):
            return self.lifecycle_service

    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_setup_logging",
        lambda self: None,
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_setup_signal_handlers",
        lambda self: None,
    )
    monkeypatch.setattr(daemon_module, "App", FakeApp)
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_start_health_monitor",
        lambda self: calls.append("health"),
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_start_api_server",
        lambda self: calls.append("api"),
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_run_loop",
        lambda self: calls.append("loop"),
    )
    monkeypatch.setattr(
        daemon_module.AIRunnerDaemon,
        "_preload_models",
        lambda self: calls.append("config-preload"),
    )

    daemon = daemon_module.AIRunnerDaemon(_daemon_config())
    daemon.start()

    app_kwargs = calls[0][1]
    assert app_kwargs["headless"] is True
    assert app_kwargs["start_headless_api_server"] is False
    assert app_kwargs["initialize_headless_lifecycle"] is False
    assert calls[1:] == [
        "initialize",
        "preload",
        "config-preload",
        "health",
        "api",
        "loop",
    ]